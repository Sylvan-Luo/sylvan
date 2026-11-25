// pku-homework：在教学网页面里执行的 JS（同源调用 Blackboard REST，用页面自己的登录状态）
window.__hw = {
  j: async u => { const r = await fetch(u); if (!r.ok) throw new Error(r.status + ' ' + u); return r.json(); },
  async all(u) { let out = [], next = u; while (next) { const d = await this.j(next); out = out.concat(d.results || []); next = d.paging && d.paging.nextPage; } return out; },
  // 列出作业。scope: 'cur' 当前学期 | 'all'
  async list(scope) {
    const ms = await this.all('/learn/api/public/v1/users/me/courses?limit=200&expand=course');
    const ok = ms.filter(m => m.availability.available === 'Yes' && m.course && m.course.availability.available === 'Yes');
    const cur = ok.length ? ok[0].course.termId : null;
    const res = [];
    await Promise.all(ok.filter(m => scope === 'all' || m.course.termId === cur).map(async m => {
      let cols = [];
      try { cols = await this.all('/learn/api/public/v2/courses/' + m.courseId + '/gradebook/columns?limit=200'); } catch (e) { return; }
      await Promise.all(cols.filter(c => c.contentId).map(async c => {
        let at = [];
        try { at = await this.all('/learn/api/public/v2/courses/' + m.courseId + '/gradebook/columns/' + c.id + '/attempts'); } catch (e) {}
        res.push({ course: m.courseId, courseName: m.course.name.replace(/\(\d\d-\d\d学年.*\)$/, ''), col: c.id, content: c.contentId,
          name: c.name, due: c.grading && c.grading.due || null, possible: c.score && c.score.possible,
          attemptsAllowed: c.grading && c.grading.attemptsAllowed || null, kind: c.scoreProviderHandle || '',
          attempts: at.map(a => ({ id: a.id, status: a.status, created: a.created, score: a.score })) });
      }));
    }));
    return res;
  },
  async detail(course, content, col) {
    const c = await this.j('/learn/api/public/v1/courses/' + course + '/contents/' + content);
    let att = []; try { att = (await this.j('/learn/api/public/v1/courses/' + course + '/contents/' + content + '/attachments')).results; } catch (e) {}
    const links = [...new DOMParser().parseFromString(c.body || '', 'text/html').querySelectorAll('a[href],img[src]')]
      .map(a => ({ text: (a.innerText || a.alt || '').trim(), href: new URL(a.getAttribute('href') || a.getAttribute('src'), location.href).href }));
    let attempts = [];
    if (col) { try { attempts = await this.all('/learn/api/public/v2/courses/' + course + '/gradebook/columns/' + col + '/attempts'); } catch (e) {} }
    for (const a of attempts) { if (a.attemptReceipt) { a.receipt = a.attemptReceipt.receiptId; a.size = a.attemptReceipt.submissionTotalSize; } }  // 学生调不了 attempts/{id}/files，文件名看提交后截图
    return { title: c.title, body: c.body || '', handler: c.contentHandler && c.contentHandler.id, avail: c.availability,
      attachments: att.map(a => ({ name: a.fileName, url: '/learn/api/public/v1/courses/' + course + '/contents/' + content + '/attachments/' + a.id + '/download' })),
      links, attempts };
  },
  // 下载为 base64（同源才带登录）
  async b64(url) {
    const r = await fetch(url); if (!r.ok) throw new Error('下载失败 ' + r.status + ' ' + url);
    const cd = r.headers.get('content-disposition') || ''; const buf = new Uint8Array(await r.arrayBuffer());
    let s = ''; for (let i = 0; i < buf.length; i += 32768) s += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
    let name = ''; const m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="?([^";]+)"?/i); if (m) { try { name = decodeURIComponent(m[1]); } catch (e) { name = m[1]; } }
    return JSON.stringify({ name, type: r.headers.get('content-type'), data: btoa(s) });
  },
  // 在上传作业页里填表：files=[{name, b64}]，text/comment 为 HTML 或纯文本
  async fill(files, text, comment) {
    const f = document.getElementById('uploadAssignmentFormId'); if (!f) return JSON.stringify({ error: '这一页不是作业上传页（可能已交满次数、已过期或不是作业）: ' + document.title });
    const setBox = (id, v) => { if (v == null) return; if (window.tinymce && tinymce.get(id)) tinymce.get(id).setContent(v); const t = document.getElementById(id); if (t) t.value = v; };
    setBox('studentSubmission.text', text); setBox('student_commentstext', comment);
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    for (const x of files) {
      const bin = atob(x.b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
      const mk = () => { const dt = new DataTransfer(); dt.items.add(new File([u], x.name)); return dt.files; };
      const before = new Set([...f.querySelectorAll('input[type=file][name^=newFile_LocalFile]')]);
      const pick = document.getElementById('newFile_chooseLocalFile'); pick.files = mk(); pick.dispatchEvent(new Event('change', { bubbles: true }));
      await sleep(800);
      const fresh = [...f.querySelectorAll('input[type=file][name^=newFile_LocalFile]')].filter(e => !before.has(e));
      if (fresh.length !== 1) return JSON.stringify({ error: '附加文件后页面没有出现新的上传项: ' + x.name });
      fresh[0].files = mk(); // 页面会清空被挪走的 input，这里把文件放回去
    }
    const fd = new FormData(f), got = [];
    for (const [k, v] of fd) if (v instanceof File && v.size) got.push(v.name + ' (' + v.size + ' B)');
    const draft = !!document.querySelector('#attempt_id') && document.querySelector('#attempt_id').value;
    const existing = [...f.querySelectorAll('[name=newFile_linkTitle]')].map(e => e.value).filter(n => !files.some(x => x.name === n));
    return JSON.stringify({ ok: true, files: got, existingDraftFiles: existing, draftAttempt: draft || null,
      text: (fd.get('studentSubmission.text') || '').slice(0, 300), comment: (fd.get('student_commentstext') || '').slice(0, 300) });
  },
  click(which) { // which: '提交' | '保存草稿'
    window.__hwMsgs = []; window.alert = m => window.__hwMsgs.push('alert: ' + m); window.confirm = m => { window.__hwMsgs.push('confirm: ' + m); return true; };
    const b = document.querySelector('[name="bottom_' + which + '"]'); if (!b) return '没找到按钮 ' + which;
    b.click(); return 'clicked ' + which + ' ' + JSON.stringify(window.__hwMsgs);
  },
};
'ok'
