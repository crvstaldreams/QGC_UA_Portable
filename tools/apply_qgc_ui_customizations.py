#!/usr/bin/env python3
from __future__ import annotations
import argparse,re,sys
from pathlib import Path
class CustomizationError(RuntimeError): pass

def _locate_unique(root: Path, filename: str, markers: tuple[str,...]) -> Path:
    matches=[]
    for path in root.rglob(filename):
        if any(part in {'.git','build','custom'} for part in path.parts): continue
        try: text=path.read_text(encoding='utf-8')
        except Exception: continue
        if all(m in text for m in markers): matches.append(path)
    if len(matches)!=1:
        raise CustomizationError(f'Expected one {filename}, found {len(matches)}')
    return matches[0]

def _sub_once(text, pattern, repl, desc):
    updated,count=re.subn(pattern,repl,text,count=1,flags=re.M)
    if count!=1: raise CustomizationError(f'Could not apply {desc}; matches={count}')
    return updated

def apply_customizations(root: Path):
    main=_locate_unique(root,'MainWindow.qml',('function showIndicatorDrawer','id: indicatorDrawer','Popup.CloseOnPressOutside'))
    status=_locate_unique(root,'MainStatusIndicator.qml',('dropMainStatusIndicator','overallStatusComponent','VehicleMessageList'))
    msgs=_locate_unique(root,'VehicleMessageList.qml',('formatMessage','<#E>','<#I>','<#N>'))

    text=main.read_text(encoding='utf-8')
    if 'function showIndicatorDrawer(drawerComponent, indicatorItem, keepOpen)' not in text:
        text=_sub_once(text,r'function\s+showIndicatorDrawer\s*\(\s*drawerComponent\s*,\s*indicatorItem\s*\)\s*\{','function showIndicatorDrawer(drawerComponent, indicatorItem, keepOpen) {','drawer signature')
        text=_sub_once(text,r'^(?P<i>[ \t]*)indicatorDrawer\.indicatorItem\s*=\s*indicatorItem\s*$',lambda m:f"{m.group('i')}indicatorDrawer.indicatorItem = indicatorItem\n{m.group('i')}indicatorDrawer.keepOpen = keepOpen === true",'drawer state')
        text=_sub_once(text,r'closePolicy:\s*Popup\.CloseOnEscape\s*\|\s*Popup\.CloseOnPressOutside','closePolicy: keepOpen ? Popup.CloseOnEscape : (Popup.CloseOnEscape | Popup.CloseOnPressOutside)','close policy')
        text=_sub_once(text,r'^(?P<i>[ \t]*)property\s+var\s+sourceComponent\s*$',lambda m:f"{m.group('i')}property var sourceComponent\n{m.group('i')}property bool keepOpen: false",'keepOpen property')
        main.write_text(text,encoding='utf-8',newline='\n')

    text=status.read_text(encoding='utf-8')
    if 'mainWindow.showIndicatorDrawer(overallStatusComponent, control, true)' not in text:
        text=_sub_once(text,r'mainWindow\.showIndicatorDrawer\s*\(\s*overallStatusComponent\s*,\s*control\s*\)','mainWindow.showIndicatorDrawer(overallStatusComponent, control, true)','status persistence')
    if 'messageFontPointSize: ScreenTools.defaultFontPointSize * 1.35' not in text:
        text=_sub_once(text,r'(VehicleMessageList\s*\{\s*\n(?P<i>[ \t]+)id:\s*vehicleMessageList\s*\n)',lambda m:m.group(1)+f"{m.group('i')}messageFontPointSize: ScreenTools.defaultFontPointSize * 1.35\n",'status font')
    status.write_text(text,encoding='utf-8',newline='\n')

    text=msgs.read_text(encoding='utf-8')
    if 'property real messageFontPointSize' not in text:
        text=_sub_once(text,r'^(?P<i>[ \t]*)property\s+bool\s+noMessages\s*:\s*messageText\.length\s*===\s*0\s*$',lambda m:f"{m.group('i')}property bool noMessages: messageText.length === 0\n{m.group('i')}property real messageFontPointSize: Math.max(1, ScreenTools.defaultFontPointSize - 1)",'message font property')
    text=text.replace('(ScreenTools.defaultFontPointSize.toFixed(0) - 1)','messageFontPointSize.toFixed(0)').replace('(ScreenTools.defaultFontPointSize - 1)','messageFontPointSize.toFixed(0)')
    msgs.write_text(text,encoding='utf-8',newline='\n')
    return [main,status,msgs]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source-root',required=True,type=Path); a=p.parse_args()
    try: changed=apply_customizations(a.source_root.resolve())
    except CustomizationError as e: print(f'QGC UI customization failed: {e}',file=sys.stderr); return 1
    for pth in changed: print('patched',pth)
    return 0
if __name__=='__main__': raise SystemExit(main())
