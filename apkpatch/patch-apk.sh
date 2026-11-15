#!/bin/bash
# Rebuild MiuiCamera.apk with A17 smali fixes. Output: apkpatch/MiuiCamera-patched.apk (unsigned, unaligned)
set -euo pipefail
export JAVA_HOME=~/Chopin/aosp/prebuilts/jdk/jdk21/linux-x86; export PATH=$JAVA_HOME/bin:$PATH
W=$(cd "$(dirname "$0")" && pwd); S=~/Chopin/toolchains/smali
APK=${1:?stock MiuiCamera.apk}
cd $W; rm -rf work; mkdir work; cd work
unzip -q -o $APK classes.dex classes2.dex
java -jar $S/baksmali-2.5.2.jar d -o smali2 classes2.dex
java -jar $S/baksmali-2.5.2.jar d -o smali1 classes.dex
(cd .. && python3 p.py >/dev/null)
java -jar $S/smali-2.5.2.jar a -a 31 -o classes2.dex smali2
java -jar $S/smali-2.5.2.jar a -a 31 -o classes.dex smali1
~/Chopin/aosp/out/host/linux-x86/bin/dexdump -d classes2.dex | grep -A40 "CameraConstructCompat;" | grep -m1 -E "invoke-direct/range.*StreamConfigurationMap;.<init>" >/dev/null && echo "dex check OK"
python3 - "$APK" "$W/MiuiCamera-patched.apk" <<'P'
import zipfile,sys
src,dst=sys.argv[1:3]
zi=zipfile.ZipFile(src); zo=zipfile.ZipFile(dst,'w')
for i in zi.infolist():
    if i.filename.startswith('META-INF/') and i.filename.split('/')[-1].split('.')[-1] in ('SF','RSA','DSA','EC','MF'): continue
    data=open(i.filename,'rb').read() if i.filename in ('classes.dex','classes2.dex') else zi.read(i)
    n=zipfile.ZipInfo(i.filename,i.date_time); n.compress_type=i.compress_type; n.external_attr=i.external_attr
    zo.writestr(n,data)
zo.close(); print('apk rebuilt')
P
cd $W; rm -rf work
