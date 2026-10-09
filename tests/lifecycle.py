from pathlib import Path
from playwright.sync_api import sync_playwright,expect
p=Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8765/index.html');expect(page.locator('#status')).to_have_text('纸面已就绪')
 page.evaluate('()=>{dispatchEvent(new PageTransitionEvent("pagehide",{persisted:true}));dispatchEvent(new PageTransitionEvent("pageshow",{persisted:true}))}')
 expect(page.locator('#status')).to_have_text('纸面已就绪')
 with page.expect_download() as d:page.click('#export')
 assert not errors
 print('pagehide/pageshow resume and actual export passed; no errors')
 b.close()
