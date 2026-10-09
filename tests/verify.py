from playwright.sync_api import sync_playwright, expect
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
import json,time,hashlib,os
P=Path(__file__).resolve().parents[1]
E=P/'evidence'; checks=[]; errors=[]; console_errors=[]; requests=[]
def check(name,ok,detail=''):
 checks.append({'check':name,'pass':bool(ok),'detail':detail});print(name,ok,detail,flush=True)
 if not ok: raise AssertionError(name)
def ready(page):expect(page.locator('#status')).to_have_text('纸面已就绪',timeout=30000)
def change(page,id,value):
 page.locator('#'+id).evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input",{bubbles:true}))}',str(value));ready(page)
def digest(page,id='result'):
 return page.locator('#'+id).evaluate('(c)=>c.toDataURL()')
def download(page,name):
 with page.expect_download(timeout=60000) as d: page.locator('#export').click()
 d.value.save_as(E/name)
 expect(page.locator('#export')).to_be_enabled(timeout=60000)
 return Image.open(E/name)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
 page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None);page.on('request',lambda r:requests.append({'url':r.url[:100],'method':r.method}))
 page.goto('http://127.0.0.1:8765/index.html');ready(page)
 check('startup',page.locator('#error').inner_text()=='')
 baseline=digest(page)
 for id,val in [('depth',85),('simplify',20),('light',120),('texture',100),('color','#dbe0d4')]:
  page.click('#reset');ready(page);change(page,id,val);check('parameter_'+id,digest(page)!=baseline)
 page.click('#reset');ready(page)
 page.click('[data-mode="-1"]');ready(page);check('concave',digest(page)!=baseline)
 page.click('#reset');ready(page);check('reset_exact',digest(page)==baseline)
 # Actual local PNG upload, repeated same-file selection, and JPG replacement.
 Image.open(P/'samples/coffee.png').save(P/'samples/coffee-upload.jpg',quality=95)
 for name in ['astronaut.png','astronaut.png','chelsea.png','coffee-upload.jpg']:
  page.set_input_files('#file',str(P/'samples'/name));ready(page);check('upload_'+name,name in page.locator('#fileinfo').inner_text())
 check('original_ratio',page.locator('#original').evaluate('(c)=>Math.abs(c.width/c.height-1.5)<.003'))
 # Every preset is actually processed and exported.
 for sample in ['coffee','chelsea','astronaut']:
  page.click('#reset');page.click('[data-sample="'+sample+'"]');ready(page)
  pic=download(page,sample+'-v1-final.png')
  check('export_'+sample,pic.format=='PNG' and max(pic.size)==1600 and ImageStat.Stat(pic).stddev[0]>1,str(pic.size))
  page.screenshot(path=str(E/(sample+'-desktop.png')),full_page=True)
 # Parameter churn must resolve exactly to final settings.
 page.locator('#depth').evaluate('(el)=>{for(let i=0;i<40;i++){el.value=(i*7)%100;el.dispatchEvent(new Event("input"))}el.value=72;el.dispatchEvent(new Event("input"))}')
 ready(page);churn=digest(page);page.wait_for_timeout(500);check('no_stale_worker',churn==digest(page))
 page.click('#reset');ready(page);change(page,'depth',72);check('churn_equals_fresh',churn==digest(page))
 # Crop and compare export dimensions/content.
 page.click('[data-sample="coffee"]');ready(page);page.select_option('#ratio','3:4');ready(page)
 check('crop_3_4',page.locator('#original').evaluate('(c)=>c.width===600&&c.height===800'))
 page.select_option('#size','2400');single=download(page,'crop-1800x2400.png');check('export_2400',single.size==(1800,2400))
 page.select_option('#format','compare');both=download(page,'compare-1800x4800.png');check('compare_size',both.size==(1800,4800))
 check('compare_bottom_matches_single',ImageChops.difference(single,both.crop((0,2400,1800,4800))).getbbox() is None)
 check('compare_top_is_color_original',ImageStat.Stat(both.crop((0,0,1800,2400))).stddev[0]>30)
 page.select_option('#size','3200');page.select_option('#format','single');big=download(page,'crop-2400x3200.png');check('export_3200',big.size==(2400,3200))
 # Rendering offline: all subsequent operations run with network disconnected.
 ctx.set_offline(True);page.click('#reset');page.click('[data-sample="chelsea"]');ready(page);change(page,'light',45)
 offline=download(page,'offline-cat.png');check('offline_change_and_export',offline.size==(1600,1064))
 page.set_input_files('#file',str(P/'samples/astronaut.png'));ready(page);check('offline_upload','astronaut.png' in page.locator('#fileinfo').inner_text())
 # Invalid file is rejected without clearing the last good image.
 good=digest(page);page.set_input_files('#file',{'name':'bad.txt','mimeType':'text/plain','buffer':b'not a photo'});check('invalid_file_preserves_photo',digest(page)==good and 'JPG' in page.locator('#error').inner_text())
 # Fresh disconnected context loads self-contained HTML bytes (no network bootstrap).
 off=b.new_context(offline=True,viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
 mobile=off.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
 mobile.set_content((P/'index.html').read_text(),wait_until='load');ready(mobile);check('offline_fresh_html',mobile.locator('#error').inner_text()=='')
 for width in [320,390,768]:
  mobile.set_viewport_size({'width':width,'height':844});check('no_overflow_'+str(width),mobile.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
 mobile.set_viewport_size({'width':390,'height':844});mobile.locator('[data-mode="-1"]').tap();ready(mobile);change(mobile,'depth',66);mobile.select_option('#ratio','3:4');ready(mobile)
 mobile.set_input_files('#file',str(P/'samples/coffee-upload.jpg'));ready(mobile)
 shot=download(mobile,'mobile-export.png');check('mobile_controls_upload_export',shot.size==(1200,1600))
 mobile.click('#reset');ready(mobile);mobile.screenshot(path=str(E/'mobile-390-v1.png'),full_page=True)
 page.click('#reset');page.click('[data-sample="coffee"]');ready(page);page.screenshot(path=str(E/'desktop-v1-final.png'),full_page=True)
 check('no_external_requests',all(r['url'].startswith(('http://127.0.0.1:8765/','blob:','data:')) for r in requests),str(requests))
 check('no_upload_requests',all(r['method']=='GET' for r in requests))
 check('no_script_errors',not errors,str(errors));check('no_console_errors',not console_errors,str(console_errors))
 report={'browser':b.version,'checks':checks,'errors':errors,'console_errors':console_errors,'requests':requests}
 (E/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 b.close()
