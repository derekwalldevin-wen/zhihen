from playwright.sync_api import sync_playwright, expect
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
import json,time,hashlib,os
P=Path(__file__).resolve().parents[1]
E=P/'evidence'; checks=[]; errors=[]; console_errors=[]; requests=[]
def check(name,ok,detail=''):
 checks.append({'check':name,'pass':bool(ok),'detail':detail});print(name,ok,detail,flush=True)
 if not ok: raise AssertionError(name)
def ready(page):expect(page.locator('#status')).to_have_text('纸面已就绪',timeout=60000)
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
 page.goto('http://127.0.0.1:8767/index.html');ready(page)
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
  pic=download(page,sample+'-v2-final.png')
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
 mobile.click('#reset');ready(mobile);mobile.screenshot(path=str(E/'mobile-390-v2.png'),full_page=True)
 page.click('#reset');page.click('[data-sample="coffee"]');ready(page);page.screenshot(path=str(E/'desktop-v2-final.png'),full_page=True)
 check('no_external_requests',all(r['url'].startswith(('http://127.0.0.1:8767/','blob:','data:')) for r in requests),str(requests))
 check('no_upload_requests',all(r['method']=='GET' for r in requests))
 check('no_script_errors',not errors,str(errors));check('no_console_errors',not console_errors,str(console_errors))
 
 # v2: actual mode outputs and shape/ink interactions.
 page.click('#reset');page.click('[data-sample="coffee"]');ready(page)
 modes={}
 for mode in ['fine','intaglio','cotton','handmade']:
  page.select_option('#paperMode',mode);ready(page);modes[mode]=digest(page)
  im=download(page,'mode-'+mode+'.png')
  check('mode_'+mode,im.size==(1600,1067))
 check('four_distinct_modes',len(set(modes.values()))==4)
 page.click('#reset');ready(page);plain=digest(page)
 page.check('#stampOn');inked=digest(page);check('stamp_enable',inked!=plain)
 page.fill('#stampText','春山可望');check('stamp_edit',digest(page)!=inked)
 page.fill('#stampText','');empty=digest(page);check('stamp_clear_keeps_border',empty!=plain and empty!=inked)
 page.uncheck('#stampOn');check('stamp_disable_no_residue',digest(page)==plain)
 page.check('#stampOn');page.fill('#stampText','PAPER 02');check('stamp_english',digest(page)!=empty)
 for bad in ['1234567890123','纸🙂','<img src=x>']:
  page.fill('#stampText',bad);check('reject_'+bad,page.locator('#stampText').input_value()==bad and page.locator('#export').is_disabled() and bool(page.locator('#stampError').inner_text()))
 check('no_html_injection',page.locator('#stampControls img').count()==0)
 page.fill('#stampText','纸上时光');check('valid_after_invalid',page.locator('#export').is_enabled())
 for id,val in [('stampSize',29),('stampOpacity',38),('ink','#394f75'),('stampX',30),('stampY',35)]:
  before=digest(page);change(page,id,val);check('stamp_parameter_'+id,digest(page)!=before)
 change(page,'stampOpacity',0);check('zero_ink_no_residue',digest(page)==plain)
 change(page,'stampOpacity',75)
 for color in ['#a34432','#34352f','#394f75']:
  page.click('[data-ink="'+color+'"]');check('ink_preset_'+color,page.locator('#ink').input_value()==color)
 # Position constraints remain valid after aspect ratio and shape changes.
 change(page,'stampSize',38);change(page,'stampX',100);change(page,'stampY',100)
 for ratio in ['3:4','1:1','4:3','original']:
  page.select_option('#ratio',ratio);ready(page)
  page.select_option('#stampShape','strip')
  bound=page.evaluate('()=>{const c=crop(source,state),w=c.ratio>=1?800:800*c.ratio,h=c.ratio>=1?800/c.ratio:800,b=stampBox(state,w,h);return state.stampX/100*w+b.sw/2<=w&&state.stampY/100*h+b.sh/2<=h}')
  check('stamp_bounds_'+ratio,bound)
 # Actual mouse pointer drag, not state injection.
 page.click('#reset');ready(page);page.check('#stampOn');page.locator('#result').scroll_into_view_if_needed()
 box=page.locator('#result').bounding_box();x=box['x']+box['width']*.8;y=box['y']+box['height']*.8
 page.mouse.move(x,y);page.mouse.down();page.mouse.move(x-box['width']*.3,y-box['height']*.3,steps=8);page.mouse.up()
 check('mouse_drag',abs(float(page.locator('#stampX').input_value())-50)<1 and abs(float(page.locator('#stampY').input_value())-50)<1)
 # Three readable stamp geometries, real downloads.
 for shape,sample,text,ink in [('square','coffee','纸上时光','#a34432'),('circle','chelsea','猫有闲','#394f75'),('strip','astronaut','PAPER 02','#34352f')]:
  page.click('#reset');page.click('[data-sample="'+sample+'"]');ready(page);page.check('#stampOn');page.select_option('#stampShape',shape);page.fill('#stampText',text);change(page,'ink',ink);page.select_option('#margin','6');ready(page)
  im=download(page,'stamp-'+shape+'.png');check('export_stamp_'+shape,im.format=='PNG')
 # Export composition must match preview stamp geometry, ink and letters.
 page.click('#reset');page.click('[data-sample="coffee"]');ready(page);page.check('#stampOn');page.fill('#stampText','春山');change(page,'stampSize',24);change(page,'stampX',68);change(page,'stampY',75)
 page.locator('#result').evaluate('(c)=>{window.previewPNG=c.toDataURL()}')
 import base64,io
 prev=Image.open(io.BytesIO(base64.b64decode(page.evaluate('()=>window.previewPNG').split(',')[1]))).convert('RGB')
 stamped=download(page,'stamp-match-single.png').convert('RGB')
 def red_bbox(im):
  import numpy as np
  a=np.asarray(im);mask=(a[:,:,0].astype(int)-a[:,:,1].astype(int)>12)&(a[:,:,0].astype(int)-a[:,:,2].astype(int)>15)
  ys,xs=np.where(mask);return [xs.min()/im.width,ys.min()/im.height,xs.max()/im.width,ys.max()/im.height]
 pb,sb=red_bbox(prev),red_bbox(stamped)
 check('stamp_preview_export_geometry',max(abs(a-b) for a,b in zip(pb,sb))<.006,str([pb,sb]))
 page.select_option('#format','compare');compare=download(page,'stamp-match-compare.png').convert('RGB')
 check('stamp_compare_bottom_exact',ImageChops.difference(stamped,compare.crop((0,stamped.height,stamped.width,stamped.height*2))).getbbox() is None)
 page.uncheck('#stampOn');page.select_option('#format','single');off=download(page,'stamp-off.png').convert('RGB');page.click('#reset');ready(page);off2=download(page,'reset-off.png').convert('RGB');check('export_disable_no_residue',ImageChops.difference(off,off2).getbbox() is None)
 # Churn across modes, text, image selections: final state wins.
 page.evaluate('()=>{for(let i=0;i<12;i++){state.paperMode=["fine","cotton","handmade","intaglio"][i%4];schedule()}state.paperMode="fine";schedule()}');ready(page);stable=digest(page);page.wait_for_timeout(600);check('mode_churn_stable',digest(page)==stable and digest(page)==plain)
 page.evaluate('()=>{load(samples.astronaut,"old");load(samples.chelsea,"middle");load(samples.coffee,"latest")}');ready(page);check('image_churn_latest','latest' in page.locator('#fileinfo').inner_text())
 # Real touch event sequence and fallback position sliders.
 mobile.check('#stampOn');mobile.locator('#result').scroll_into_view_if_needed();box=mobile.locator('#result').bounding_box();sx=box['x']+box['width']*.8;sy=box['y']+box['height']*.8
 cdp=off_context_cdp=mobile.context.new_cdp_session(mobile)
 cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':sx,'y':sy}]})
 cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':sx-box['width']*.25,'y':sy-box['height']*.25}]})
 cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
 check('touch_drag',abs(float(mobile.locator('#stampX').input_value())-55)<2)
 change(mobile,'stampX',0);check('mobile_boundary_slider',float(mobile.locator('#stampX').input_value())>0)
 for shape in ['square','circle','strip']:mobile.select_option('#stampShape',shape)
 mobile.fill('#stampText','纸上春天');mobile.select_option('#margin','6');ready(mobile)
 for width in [320,390,768]:
  mobile.set_viewport_size({'width':width,'height':844});check('v2_no_overflow_'+str(width),mobile.evaluate('()=>document.documentElement.scrollWidth<=innerWidth'))
 mobile.set_viewport_size({'width':390,'height':844});mobile.evaluate('()=>scrollTo(0,0)');mobile.screenshot(path=str(E/'mobile-v2-final.png'),full_page=True)
 page.click('#reset');page.check('#stampOn');page.select_option('#paperMode','handmade');page.select_option('#margin','6');ready(page);page.evaluate('()=>scrollTo(0,0)');page.screenshot(path=str(E/'desktop-v2-final.png'),full_page=True)
 check('v2_no_script_errors',not errors,str(errors));check('v2_no_console_errors',not console_errors,str(console_errors))

 report={'browser':b.version,'checks':checks,'errors':errors,'console_errors':console_errors,'requests':requests}
 (E/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 b.close()
