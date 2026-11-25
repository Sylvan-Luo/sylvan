# pku-homework：在用户笔记本的专用 Chrome（9222）里操作教学网。由 hw 拼在每条命令前面。
# 只用自己的标签（id 记在 %LOCALAPPDATA%\ClaudeChrome\hw_tab.txt），不动别的会话的标签。
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$HwDir="$env:LOCALAPPDATA\ClaudeHw"; New-Item -ItemType Directory -Force $HwDir | Out-Null
$Portal='https://course.pku.edu.cn/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_1_1'
function Tabs{ try{ $a=((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:9222/json/list).Content | ConvertFrom-Json) }catch{ throw 'NOCHROME 专用 Chrome 没开（先 pcweb start）' }; @($a) | Where-Object {$_.type -eq 'page'} }
function HwTab{
  $f="$env:LOCALAPPDATA\ClaudeChrome\hw_tab.txt"; $t=@(Tabs)
  if(Test-Path $f){ $id=(Get-Content $f).Trim(); $m=$t|?{$_.id -eq $id}; if($m){ return $m } }
  $n=(Invoke-WebRequest -UseBasicParsing -Method Put ("http://127.0.0.1:9222/json/new?"+$Portal)).Content|ConvertFrom-Json
  Set-Content $f $n.id; Start-Sleep 3; return $n
}
function Cdp($tab,$method,$params){
  $ws=New-Object System.Net.WebSockets.ClientWebSocket; $ws.Options.KeepAliveInterval=[TimeSpan]::Zero
  $ws.ConnectAsync([Uri]$tab.webSocketDebuggerUrl,[Threading.CancellationToken]::None).Wait()
  $msg=@{id=1;method=$method;params=$params}|ConvertTo-Json -Depth 10 -Compress
  $b=[Text.Encoding]::UTF8.GetBytes($msg)
  $ws.SendAsync((New-Object 'ArraySegment[byte]' -ArgumentList (,$b)),[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).Wait()
  $ms=New-Object IO.MemoryStream; $buf=New-Object byte[] 1048576
  while($true){ $seg=New-Object 'ArraySegment[byte]' -ArgumentList (,$buf); $r=$ws.ReceiveAsync($seg,[Threading.CancellationToken]::None); $r.Wait(); $ms.Write($buf,0,$r.Result.Count)
    if($r.Result.EndOfMessage){ $s=[Text.Encoding]::UTF8.GetString($ms.ToArray()); if($s -match '"id":1[,}]'){break}; $ms.SetLength(0)} }
  $ws.Dispose(); return ($s|ConvertFrom-Json)
}
# 在 hw 标签里执行 JS（可 await），返回字符串
function Ev($js){
  $r=Cdp (HwTab) 'Runtime.evaluate' @{expression=$js;returnByValue=$true;awaitPromise=$true}
  if($r.result.exceptionDetails){ throw ('JSERR '+$r.result.exceptionDetails.exception.description) }
  $v=$r.result.result.value; if($v -is [string]){$v}else{$v|ConvertTo-Json -Depth 8 -Compress}
}
function Nav($url){
  $t=HwTab; Cdp $t 'Page.navigate' @{url=$url} | Out-Null
  foreach($i in 1..40){ Start-Sleep -Milliseconds 500; try{ if((Ev 'document.readyState') -eq 'complete'){ break } }catch{} }
}
function B64($s){ [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($s)) }
# 保证 hw 标签停在教学网（REST 要同源）；未登录时抛 LOGIN
function Ready{
  $u=''; try{ $u=Ev 'location.href' }catch{}
  if($u -notlike 'https://course.pku.edu.cn/*'){ Nav $Portal }
  $s=Ev 'fetch("/learn/api/public/v1/users/me").then(r=>String(r.status))'
  if($s -ne '200'){ throw 'LOGIN 教学网没登录（或掉线了）：请用户在专用 Chrome 窗口里重新登录 course.pku.edu.cn' }
}
