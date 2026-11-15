import os
FINAL=os.environ.get('CHOPIN_FINAL')=='1'
ROM=os.environ.get('CHOPIN_ROM')=='1'  # ROM build: frameworks/av takes fractional I-frame intervals, skip v12  # v19: final build drops debug.chopin.* toggles (stock paths)
import re,sys
f='work/smali2/com/xiaomi/compat/camera2/CameraConstructCompat.smali'
s=open(f).read()
m=re.search(r'\.method public static getStreamConfigurationMap\((.*?)\)(\S+)\n.*?\.end method\n', s, re.S)
assert m
SC='[Landroid/hardware/camera2/params/StreamConfiguration;'; SD='[Landroid/hardware/camera2/params/StreamConfigurationDuration;'
ctor='('+ (SC+SD+SD)*6 +'[Landroid/hardware/camera2/params/HighSpeedVideoConfiguration;Landroid/hardware/camera2/params/ReprocessFormatsMap;Z)V'
body=[f'.method public static getStreamConfigurationMap({m.group(1)}){m.group(2)}',
'    .registers 37',
'    # chopin A17: call the 21-arg ctor (jpegR + heicUltraHDR arrays = null) directly; A13/U reflection signature no longer exists',
'    new-instance v0, Landroid/hardware/camera2/params/StreamConfigurationMap;']
for i in range(12): body.append(f'    move-object/from16 v{i+1}, p{i}')
for r in range(13,19): body.append(f'    const/16 v{r}, 0x0' if r>15 else f'    const/4 v{r}, 0x0')
body+= ['    move-object/from16 v19, p12','    move-object/from16 v20, p13','    move/from16 v21, p14',
f'    invoke-direct/range {{v0 .. v21}}, Landroid/hardware/camera2/params/StreamConfigurationMap;-><init>{ctor}',
'    return-object v0','.end method','']
s=s[:m.start()]+'\n'.join(body)+s[m.end():]
open(f,'w').write(s)
print('\n'.join(body))

# v7: v4 forced isForceMainBackCamera() globally -> portrait on phys cam 0 asks a Y16 (0x20363159) depth stream cam 0
# does not have (onConfigureFailed -> "can't connect"). Now force main back cam 0 only in
# Camera2DataContainer.getActualOpenCameraId for modules other than portrait (0xab = 171); portrait keeps logical bokeh cam.
import re
f='work/smali1/com/android/camera/module/loader/camera2/Camera2DataContainer.smali'
s=open(f).read()
i=s.index('.method public declared-synchronized getActualOpenCameraId(II)I'); j=s.index('.end method', i)
body=s[i:j]
pat=re.compile(r'invoke-virtual \{v4\}, Lcom/android/camera/data/data/global/DataItemGlobal;->isForceMainBackCamera\(\)Z\s*(?:\.line \d+\s*)?move-result v4')
assert len(pat.findall(body))==1, 'force pattern count %d' % len(pat.findall(body))
body=pat.sub('''# chopin v10: logical cam by default (stock); debug.chopin.miuicam.forcemain=true forces phys main back cam except portrait (171)
    const-string v4, "debug.chopin.miuicam.forcemain"

    const/4 v5, 0x0

    invoke-static {v4, v5}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z

    move-result v4

    const/16 v5, 0xab

    if-ne p2, v5, :chopin_force_x

    const/4 v4, 0x0

    :chopin_force_x''', body)
s=s[:i]+body+s[j:]
if not FINAL: open(f,'w').write(s)

# ---- v5: stub MIUI framework classes the app looks up (all optional on stock; missing on LOS) ----
import os
def W(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True); open(path,'w').write(text)
def ret_false(sig, regs):
    return f'''.method public {sig}
    .registers {regs}
    const/4 v0, 0x0
    return v0
.end method
'''
# android.util.MtkBoostFramework: BoostFrameworkImpl reflects ctor(), perfLockAcquire(int,int[]), perfLockRelease(). No-op (no mtkpower access from app).
W('work/smali2/android/util/MtkBoostFramework.smali', '''.class public Landroid/util/MtkBoostFramework;
.super Ljava/lang/Object;
# chopin v5 stub: MIUI camera perf lock entry point; no-op on LOS
.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method
.method public varargs perfLockAcquire(I[I)I
    .registers 4
    const/4 v0, -0x1
    return v0
.end method
.method public perfLockRelease()I
    .registers 2
    const/4 v0, -0x1
    return v0
.end method
''')
# miui.process.ProcessManager.adjBoost(String,int,long,int): Util.adjBoost reflects it (parallel service adj boost). No-op.
W('work/smali2/miui/process/ProcessManager.smali', '''.class public Lmiui/process/ProcessManager;
.super Ljava/lang/Object;
# chopin v5 stub
.method public static adjBoost(Ljava/lang/String;IJI)V
    .registers 6
    return-void
.end method
''')
# miui.util.HapticFeedbackUtil: miuix PlatformConstants uses it directly; return false so callers fall back to AOSP haptics.
h = ['.class public Lmiui/util/HapticFeedbackUtil;', '.super Ljava/lang/Object;', '# chopin v5 stub',
'''.method public constructor <init>(Landroid/content/Context;Z)V
    .registers 3
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method''',
'''.method public release()V
    .registers 1
    return-void
.end method''',
'''.method public stop()V
    .registers 1
    return-void
.end method''']
for sig, regs in [('isSupportExtHapticFeedback(I)Z',3),('isSupportLinearMotorVibrate()Z',2),('isSupportLinearMotorVibrate(I)Z',3),
    ('performExtHapticFeedback(I)Z',3),('performExtHapticFeedback(IDLjava/lang/String;)Z',6),('performExtHapticFeedback(II)Z',4),
    ('performExtHapticFeedback(IIZ)Z',5),('performExtHapticFeedback(IZ)Z',4),('performExtHapticFeedback(Landroid/net/Uri;)Z',3),
    ('performExtHapticFeedback(Landroid/net/Uri;Z)Z',4),('performHapticFeedback(IDLjava/lang/String;)Z',6),
    ('performHapticFeedback(IZ)Z',4),('performHapticFeedback(IZI)Z',5)]:
    h.append(ret_false(sig, regs))
W('work/smali2/miui/util/HapticFeedbackUtil.smali', '\n'.join(h)+'\n')

# ---- v5 test forced EIS off (Vidhance suspected in heap corruption under the debug kernel).
# v15: EIS back to stock; `setprop debug.chopin.miuicam.noeis true` + app restart = v5 behaviour (no EIS).
PROP_CHECK = """
    # chopin v15: debug.chopin.miuicam.noeis -> no EIS
    const-string v0, "debug.chopin.miuicam.noeis"
    const/4 v1, 0x0
    invoke-static {v0, v1}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z
    move-result v0
"""
def inject(path, sig, tail):
    if FINAL: return
    s = open(path).read()
    i = s.index(sig); m = re.compile(r'\.registers (\d+)\n').search(s, i)
    assert m and m.start() < s.index('.end method', i)
    n = int(m.group(1)) + 2
    s = s[:m.start()] + '.registers %d\n' % n + PROP_CHECK + tail + s[m.end():]
    open(path, 'w').write(s)
inject('work/smali2/com/android/camera2/CameraConfigs.smali', '.method public setEnableEIS(Z)Z', """    if-eqz v0, :chopin_eis_ok
    const/4 p1, 0x0
    :chopin_eis_ok
""")
inject('work/smali2/com/android/camera2/CameraCapabilities.smali', '.method public isEISPreviewSupported()Z', """    if-eqz v0, :chopin_eisp_ok
    const/4 v0, 0x0
    return v0
    :chopin_eisp_ok
""")

# ---- v9: photo (and every non-portrait back module) runs on forced phys cam 0, but getDefaultParallelOpModeOnce still
# picked SESSION_OPERATION_MODE_ALGO_UP_SAT (0x9002). HAL then runs MI_FEATURE_ARCSOFT_SAT on a single sensor:
# GetCameraType fails, fZoomRatio inf, no LDC info -> __stack_chk_fail in SArcSat::process (tombstones 11-14, 2026-11-15).
# Use ALGO_UP_NORMAL (0x9005) instead; portrait does not use this path.
f='work/smali1/com/android/camera/features/mode/CameraModuleDeviceParam.smali'
s=open(f).read()
i=s.index('.method private getDefaultParallelOpModeOnce()I'); j=s.index('.end method', i)
body=s[i:j]
assert body.count('const v1, 0x9002')==1
body=body.replace('const v1, 0x9002', """# chopin v10: SAT (stock) unless forcemain (phys cam 0 cannot run SAT)
    const v1, 0x9002
    const-string v0, "debug.chopin.miuicam.forcemain"
    const/4 p0, 0x0
    invoke-static {v0, p0}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z
    move-result v0
    if-eqz v0, :chopin_sat_ok
    const v1, 0x9005
    :chopin_sat_ok""")
s=s[:i]+body+s[j:]
if not FINAL: open(f,'w').write(s)

# v12: slow-mo 960 = 240 fps source + app frame interpolation. App asks MediaRecorder for
# "video-param-i-frames-interval=<8/fps>" (an I-frame every 8 frames) because the interpolator's normal-speed
# segments decode only every 8th sample (FRAME_SKIP_SIZE_ORIGIN_SPEED_TO_NORMAL=8). AOSP StagefrightRecorder only
# parses integer seconds -> -22, GOP stays 240 -> P-frames decoded without refs -> blocky/colour-smeared output.
# Module fix: ask for interval 0 (all-intra, AOSP-supported). Tree fix: accept float interval in StagefrightRecorder.
if not ROM:
    f='work/smali1/com/android/camera/module/video/RecorderController.smali'
    s=open(f).read()
    n=s.count('"video-param-i-frames-interval=0.033"'); assert n==1, n
    s=s.replace('"video-param-i-frames-interval=0.033"','"video-param-i-frames-interval=0"')
    for r in ('v1','v3'):
        pat=re.compile(r'(invoke-virtual \{'+r+r', v4, v5\}, Ljava/text/DecimalFormat;->format\(D\)Ljava/lang/String;\s*move-result-object '+r+r'\n)')
        assert len(pat.findall(s))==1, r
        s=pat.sub(lambda m: m.group(1)+'\n    # chopin v12: integer interval (all-intra)\n    const-string '+r+', "0"\n', s)
    open(f,'w').write(s)
    print('v12 iframe patch ok')

# v14: ICustomCaptureResult.toTotalCaptureResult(IZ) reflected CaptureResultExtras with the A13 11-arg and Q 8-arg
# ctors; A17 has 13 args -> NoSuchMethodException -> "null capture result!" (ParallelTaskData.setCaptureResult null).
# Also picked "first TotalCaptureResult ctor with >2 params" (ambiguous on A17). Replace with a direct call to the
# A17 TotalCaptureResult(String,CameraMetadataNative,CaptureRequest,int requestId,long frameNumber,List,int sessionId,
# PhysicalCaptureResultInfo[]) ctor (stock's SDK>30 branch args), which needs no CaptureResultExtras.
f='work/smali2/com/xiaomi/protocol/ICustomCaptureResult.smali'
s=open(f).read()
sig='.method public static toTotalCaptureResult(Lcom/xiaomi/protocol/ICustomCaptureResult;IZ)Landroid/hardware/camera2/TotalCaptureResult;'
i=s.index(sig); j=s.index('.end method', i)+len('.end method')
C='Lcom/xiaomi/protocol/ICustomCaptureResult;'
body=sig+'''
    .registers 16
    # chopin v14: direct A17 ctor, no reflection
    :try_start_0
    if-eqz p2, :chopin_logical
    invoke-virtual {p0}, '''+C+'''->getMainPhysicalResult()Landroid/os/Parcelable;
    move-result-object v0
    if-nez v0, :chopin_have
    :chopin_logical
    invoke-virtual {p0}, '''+C+'''->getResults()Landroid/os/Parcelable;
    move-result-object v0
    :chopin_have
    invoke-static {v0}, '''+C+'''->getCameraMetaDataCopy(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v2
    if-nez v2, :chopin_meta_ok
    const/4 v0, 0x0
    return-object v0
    :chopin_meta_ok
    check-cast v2, Landroid/hardware/camera2/impl/CameraMetadataNative;
    invoke-virtual {p0}, '''+C+'''->getRequest()Landroid/hardware/camera2/CaptureRequest;
    move-result-object v3
    invoke-static {v3}, '''+C+'''->retrieveLogicalCameraId(Landroid/hardware/camera2/CaptureRequest;)Ljava/lang/String;
    move-result-object v1
    invoke-virtual {p0}, '''+C+'''->getSequenceId()I
    move-result v4
    invoke-virtual {p0}, '''+C+'''->getFrameNumber()J
    move-result-wide v5
    const/4 v7, 0x0
    move/from16 v8, p1
    const/4 v9, 0x0
    new-array v9, v9, [Landroid/hardware/camera2/impl/PhysicalCaptureResultInfo;
    new-instance v0, Landroid/hardware/camera2/TotalCaptureResult;
    invoke-direct/range {v0 .. v9}, Landroid/hardware/camera2/TotalCaptureResult;-><init>(Ljava/lang/String;Landroid/hardware/camera2/impl/CameraMetadataNative;Landroid/hardware/camera2/CaptureRequest;IJLjava/util/List;I[Landroid/hardware/camera2/impl/PhysicalCaptureResultInfo;)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :chopin_catch
    return-object v0
    :chopin_catch
    move-exception v0
    sget-object v1, '''+C+'''->TAG:Ljava/lang/String;
    const-string v2, "chopin: toTotalCaptureResult failed"
    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I
    const/4 v0, 0x0
    return-object v0
.end method'''
s=s[:i]+body+s[j:]
open(f,'w').write(s)
print('v14 totalcaptureresult patch ok')
