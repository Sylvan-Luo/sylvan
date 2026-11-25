-- boxes.lua —— 把 Markdown 里的 ::: 块和 [..]{.类} 行内标记翻成 latex-pdf-theme 的环境/命令
-- 用法见 ~/tools/latex-pdf/README.md

local fix_latex  -- 下面定义

local function latex(inlines_or_blocks)
  local doc
  if inlines_or_blocks == nil then return '' end
  if inlines_or_blocks.t == nil and #inlines_or_blocks > 0 and inlines_or_blocks[1].t
     and pandoc.utils.type(inlines_or_blocks[1]) == 'Inline' then
    doc = pandoc.Pandoc({pandoc.Plain(inlines_or_blocks)})
  elseif pandoc.utils.type(inlines_or_blocks) == 'Inlines' then
    doc = pandoc.Pandoc({pandoc.Plain(inlines_or_blocks)})
  else
    doc = pandoc.Pandoc(inlines_or_blocks)
  end
  local s = pandoc.write(doc, 'latex')
  return fix_latex((s:gsub('%s+$', '')))
end

local function md_inline(str)
  -- 把属性里的字符串（可能含 $公式$、**粗体**）当 Markdown 解析成 LaTeX
  if str == nil or str == '' then return '' end
  local d = pandoc.read(str, 'markdown')
  if #d.blocks == 0 then return '' end
  local b = d.blocks[1]
  if b.content then return latex(b.content) end
  return latex(d.blocks)
end

local function raw(s) return pandoc.RawBlock('latex', s) end
local function rawi(s) return pandoc.RawInline('latex', s) end

-- ---------------------------------------------------------------- Unicode 上下标与数学符号
-- 正文字体（Termes/宋体）缺 ᵢ ₁ ≡ ⇒ ∫ 之类字形，会打成空白：
-- 上下标字符 → \textsubscript / \textsuperscript，数学符号 → \ensuremath（STIX Two Math）
local SUB = {}
for k, v in pairs({['₀']='0',['₁']='1',['₂']='2',['₃']='3',['₄']='4',['₅']='5',['₆']='6',['₇']='7',
  ['₈']='8',['₉']='9',['₊']='+',['₋']='-',['₌']='=',['₍']='(',['₎']=')',['ₐ']='a',['ₑ']='e',['ₒ']='o',
  ['ₓ']='x',['ₕ']='h',['ₖ']='k',['ₗ']='l',['ₘ']='m',['ₙ']='n',['ₚ']='p',['ₛ']='s',['ₜ']='t',
  ['ᵢ']='i',['ᵣ']='r',['ᵤ']='u',['ᵥ']='v',['ⱼ']='j',['ᵦ']='$\\beta$',['ᵧ']='$\\gamma$',
  ['ᵨ']='$\\rho$',['ᵩ']='$\\phi$',['ᵪ']='$\\chi$'}) do SUB[utf8.codepoint(k)] = v end
local SUP = {}
for k, v in pairs({['⁰']='0',['⁴']='4',['⁵']='5',['⁶']='6',['⁷']='7',['⁸']='8',['⁹']='9',['⁺']='+',
  ['⁻']='-',['⁼']='=',['⁽']='(',['⁾']=')',['ⁿ']='n',['ⁱ']='i',['ᵃ']='a',['ᵇ']='b',['ᶜ']='c',['ᵈ']='d',
  ['ᵉ']='e',['ᶠ']='f',['ᵍ']='g',['ʰ']='h',['ʲ']='j',['ᵏ']='k',['ˡ']='l',['ᵐ']='m',['ᵒ']='o',['ᵖ']='p',
  ['ʳ']='r',['ˢ']='s',['ᵗ']='t',['ᵘ']='u',['ᵛ']='v',['ʷ']='w',['ˣ']='x',['ʸ']='y',['ᶻ']='z',
  ['ᴬ']='A',['ᴮ']='B',['ᴰ']='D',['ᴱ']='E',['ᴳ']='G',['ᴴ']='H',['ᴵ']='I',['ᴶ']='J',['ᴷ']='K',
  ['ᴸ']='L',['ᴹ']='M',['ᴺ']='N',['ᴼ']='O',['ᴾ']='P',['ᴿ']='R',['ᵀ']='T',['ᵁ']='U',['ⱽ']='V',
  ['ᵂ']='W'}) do SUP[utf8.codepoint(k)] = v end
local function is_mathsym(c)
  return (c >= 0x2190 and c <= 0x23FF) or (c >= 0x2032 and c <= 0x2037)
      or (c >= 0x27C0 and c <= 0x27FF) or (c >= 0x2900 and c <= 0x2AFF)
      or (c >= 0x1D400 and c <= 0x1D7FF)
end
local function special(c) return SUB[c] or SUP[c] or is_mathsym(c) end

-- 把文字切成 { {'text', s}, {'tex', s}, … }
local function split_special(text)
  local parts, buf, mode, run = {}, {}, nil, {}
  local function flush_run()
    if #run > 0 then
      local cmd = mode == 'sub' and '\\textsubscript{' or '\\textsuperscript{'
      parts[#parts + 1] = {'tex', cmd .. table.concat(run) .. '}'}
      run = {}
    end
    mode = nil
  end
  local function flush_buf()
    if #buf > 0 then parts[#parts + 1] = {'text', table.concat(buf)}; buf = {} end
  end
  for _, c in utf8.codes(text) do
    if SUB[c] or SUP[c] then
      local m = SUB[c] and 'sub' or 'sup'
      flush_buf()
      if mode ~= m then flush_run(); mode = m end
      run[#run + 1] = SUB[c] or SUP[c]
    elseif is_mathsym(c) then
      flush_buf(); flush_run()
      parts[#parts + 1] = {'tex', '\\ensuremath{' .. utf8.char(c) .. '}'}
    else
      flush_run()
      buf[#buf + 1] = utf8.char(c)
    end
  end
  flush_buf(); flush_run()
  return parts
end

local function has_special(text)
  for _, c in utf8.codes(text) do if special(c) then return true end end
  return false
end

function Str(el)
  if not has_special(el.text) then return nil end
  local out = pandoc.Inlines({})
  for _, p in ipairs(split_special(el.text)) do
    if p[1] == 'text' then out:insert(pandoc.Str(p[2])) else out:insert(rawi(p[2])) end
  end
  return out
end

-- 已经是 LaTeX 的字符串（框标题等）：直接替换
fix_latex = function(s)
  if not has_special(s) then return s end
  local r = {}
  for _, p in ipairs(split_special(s)) do r[#r + 1] = p[2] end
  return table.concat(r)
end

-- 类名 → { 环境, 种类, 默认标签 }
-- titled：带标题条和编号；strip：左竖条 + 行首标签；plain：无参数
local BOXES = {
  def = {'lpdef', 'titled', '定义'}, definition = {'lpdef', 'titled', '定义'},
  thm = {'lpthm', 'titled', '结论'}, theorem = {'lpthm', 'titled', '定理'},
  conclusion = {'lpthm', 'titled', '结论'},
  example = {'lpexample', 'titled', '例'},
  warn = {'lpwarn', 'strip', '易错'}, warning = {'lpwarn', 'strip', '注意'},
  pitfall = {'lpwarn', 'strip', '易错'},
  intuition = {'lpintuition', 'strip', '直觉'},
  tip = {'lptip', 'strip', '要点'}, exam = {'lptip', 'strip', '考场写法'},
  note = {'lpnote', 'strip', '注'},
  quote = {'lpquote', 'opt', '引用'}, said = {'lpquote', 'opt', '原话'},
  guide = {'lpguide', 'opt', '学习指南'},
  info = {'lpinfo', 'opt', ''},
  key = {'lpkey', 'plain'}, formula = {'lpkey', 'plain'},
  answer = {'lpanswer', 'plain'},
  card = {'lpcard', 'plain'},
}
local ORDER = {'def','definition','thm','theorem','conclusion','example','warn','warning',
  'pitfall','intuition','tip','exam','note','quote','said','guide','info','key','formula','answer','card'}

local TAGCOLORS = {red='lpwarn', orange='lpquote', green='lpthm', blue='lpdef',
  purple='lpintu', pink='lptip', gray='lpgray', grey='lpgray', yellow='lpkeyframe'}
local TAGWORDS = {['必会']='lpwarn', ['重点']='lpwarn', ['必考']='lpwarn', ['常考']='lptip',
  ['了解']='lpgray', ['补充']='lpgray', ['选读']='lpgray', ['新']='lpthm'}

local function has(el, c) return el.classes:includes(c) end

-- 原话块里以 —— 开头的段落 → 右对齐署名
local function attribution(blk)
  if (blk.t == 'Para' or blk.t == 'Plain') and #blk.content > 0 and blk.content[1].t == 'Str' then
    local s = blk.content[1].text
    if s:sub(1, 6) == '——' or s:sub(1, 2) == '--' then
      local rest = pandoc.List(blk.content)
      local first = s:gsub('^——%s*', ''):gsub('^%-%-+%s*', '')
      if first == '' then rest:remove(1) else rest[1] = pandoc.Str(first) end
      while #rest > 0 and (rest[1].t == 'Space') do rest:remove(1) end
      return raw('\\lpattrib{' .. latex(rest) .. '}')
    end
  end
  return blk
end

local function choices(div)
  local cols = tonumber(div.attributes.cols or '') or 2
  local out = {}
  local buf = {'\\begin{lpchoices}{' .. cols .. '}%'}
  local letters = {'A','B','C','D','E','F','G','H'}
  for _, b in ipairs(div.content) do
    if b.t == 'BulletList' or b.t == 'OrderedList' then
      for i, item in ipairs(b.content) do
        local body = latex(item)
        local label = '(' .. (letters[i] or tostring(i)) .. ')'
        -- 已经自带 (A) / A. / A、 的，用它自己的
        local own, rest = body:match('^%(?(%u)[%)%.、]%s*(.*)$')
        if own then label = '(' .. own .. ')'; body = rest end
        body = body:gsub('\n%s*\n', '\\par ')
        buf[#buf + 1] = '\\lpchoice{' .. label .. '}{' .. body .. '}%'
      end
    else
      out[#out + 1] = b
    end
  end
  buf[#buf + 1] = '\\end{lpchoices}'
  table.insert(out, 1, raw(table.concat(buf, '\n')))
  return out
end

function Div(div)
  if has(div, 'choices') then return choices(div) end
  for _, cls in ipairs(ORDER) do
    if has(div, cls) then
      local spec = BOXES[cls]
      local env, kind, deflabel = spec[1], spec[2], spec[3]
      local content = pandoc.List(div.content)
      -- 标题：title 属性，或块里第一个标题行
      local title = md_inline(div.attributes.title)
      if title == '' and #content > 0 and content[1].t == 'Header' then
        title = latex(content[1].content)
        content:remove(1)
      end
      local label = div.attributes.label and md_inline(div.attributes.label) or deflabel
      if cls == 'quote' or cls == 'said' then
        content = content:map(attribution)
      end
      local open
      if kind == 'titled' then
        local star = has(div, 'unnumbered') and '*' or ''
        open = '\\begin{' .. env .. star .. '}[' .. label .. ']{' .. title .. '}'
        env = env .. star
      elseif kind == 'strip' then
        if title ~= '' then label = title end
        open = '\\begin{' .. env .. '}[' .. label .. ']'
      elseif kind == 'opt' then
        if title ~= '' then label = title end
        if env == 'lpinfo' then
          open = '\\begin{lpinfo}' .. (label ~= '' and ('[title={' .. label .. '}]') or '')
        else
          open = '\\begin{' .. env .. '}[' .. label .. ']'
        end
      else
        open = '\\begin{' .. env .. '}'
      end
      local out = pandoc.List()
      if kind == 'strip' and #content > 0 and (content[1].t == 'Para' or content[1].t == 'Plain') then
        local first = pandoc.List({rawi(open)}); first:extend(content[1].content)
        content[1] = pandoc.Para(first)
      else
        out:insert(raw(open))
      end
      out:extend(content)
      out:insert(raw('\\end{' .. env .. '}'))
      return out
    end
  end
  if has(div, 'center') then
    local out = pandoc.List({raw('\\begin{center}')}); out:extend(div.content)
    out:insert(raw('\\end{center}')); return out
  end
  if has(div, 'newpage') or has(div, 'pagebreak') then return raw('\\clearpage') end
end

local function wrapi(pre, content, post)
  local out = pandoc.Inlines({rawi(pre)})
  out:extend(content)
  out:insert(rawi(post))
  return out
end

function Span(sp)
  if has(sp, 'tag') then
    local color = sp.attributes.color
    for _, c in ipairs(sp.classes) do if TAGCOLORS[c] then color = TAGCOLORS[c] end end
    if not color then color = TAGWORDS[pandoc.utils.stringify(sp.content)] or 'lpgray' end
    if TAGCOLORS[color] then color = TAGCOLORS[color] end
    return wrapi('\\lptag[' .. color .. ']{', sp.content, '}')
  elseif has(sp, 'src') then
    return wrapi('\\lpsrc{', sp.content, '}')
  elseif has(sp, 'hl') then
    return wrapi('\\lphl{', sp.content, '}')
  elseif has(sp, 'mark') then
    return wrapi('\\lpmarker{', sp.content, '}')
  elseif has(sp, 'kai') then
    return wrapi('{\\kaishu ', sp.content, '}')
  elseif has(sp, 'blank') then
    local w = sp.attributes.width or '4em'
    return rawi('\\lpblank[' .. w .. ']')
  end
end

-- GitHub 风格提示块：> [!NOTE] / [!TIP] / [!WARNING] / [!IMPORTANT] / [!CAUTION]
local ALERTS = {NOTE='lpnote', TIP='lptip', IMPORTANT='lpthm*', WARNING='lpwarn', CAUTION='lpwarn'}
local ALERTLABEL = {NOTE='注', TIP='提示', IMPORTANT='重要', WARNING='注意', CAUTION='小心'}
function BlockQuote(bq)
  local first = bq.content[1]
  if first and (first.t == 'Para' or first.t == 'Plain') and first.content[1]
     and first.content[1].t == 'Str' then
    local kind = first.content[1].text:match('^%[!(%u+)%]$')
    if kind and ALERTS[kind] then
      local rest = pandoc.List(first.content)
      rest:remove(1)
      while #rest > 0 and (rest[1].t == 'SoftBreak' or rest[1].t == 'Space' or rest[1].t == 'LineBreak') do
        rest:remove(1)
      end
      local blocks = pandoc.List(bq.content)
      if #rest > 0 then blocks[1] = pandoc.Para(rest) else blocks:remove(1) end
      local env = ALERTS[kind]
      local open = env == 'lpthm*' and ('\\begin{lpthm*}[' .. ALERTLABEL[kind] .. ']{}')
                   or ('\\begin{' .. env .. '}[' .. ALERTLABEL[kind] .. ']')
      local out = pandoc.List()
      if env ~= 'lpthm*' and #blocks > 0 and blocks[1].t == 'Para' then
        local f = pandoc.List({rawi(open)}); f:extend(blocks[1].content)
        blocks[1] = pandoc.Para(f)
      else
        out:insert(raw(open))
      end
      out:extend(blocks)
      out:insert(raw('\\end{' .. env .. '}'))
      return out
    end
  end
end

-- 书籍里无编号的一级标题（# 考前须知 {-}）也写进页眉
local is_book = false
function Meta(m)
  is_book = m.book and true or false
  if m.info then
    local items = {}
    for _, entry in ipairs(m.info) do
      if pandoc.utils.type(entry) == 'table' or type(entry) == 'table' then
        for k, v in pairs(entry) do
          local val
          local ty = pandoc.utils.type(v)
          if ty == 'Inlines' then val = latex(v)
          elseif ty == 'Blocks' then val = latex(v)
          else val = pandoc.utils.stringify(v) end
          items[#items + 1] = '\\item[' .. k .. '] ' .. val
        end
      end
    end
    m['info-latex'] = pandoc.MetaBlocks({raw('\\begin{description}\n' ..
      table.concat(items, '\n') .. '\n\\end{description}')})
  end
  return m
end

local in_unnumbered = false
function Header(h)
  if is_book and h.level == 1 and h.classes:includes('part') then
    local out = {raw('\\part{' .. latex(h.content) .. '}')}
    if h.classes:includes('restart') then out[#out + 1] = raw('\\setcounter{chapter}{0}') end
    in_unnumbered = false
    return out
  end
  if is_book and h.level == 1 then
    in_unnumbered = h.classes:includes('unnumbered')
    if in_unnumbered then return {h, raw('\\lpmark{' .. latex(h.content) .. '}')} end
  elseif is_book and in_unnumbered and not h.classes:includes('unnumbered') then
    h.classes:insert('unnumbered')
    return h
  end
end

return {
  {Meta = Meta},
  {Str = Str},
  {Div = Div, Span = Span, BlockQuote = BlockQuote, Header = Header},
}
