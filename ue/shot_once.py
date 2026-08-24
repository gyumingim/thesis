"""장면 1샷 후 종료. SHOT_LEVEL/SHOT_OUT/SHOT_DELAY 환경변수 사용, filename= 직접 지정."""
import unreal, os, time
LEVEL = os.environ.get("SHOT_LEVEL", "/Game/GenScenes/proto_v4")
OUTPNG = os.environ.get("SHOT_OUT", "C:/ue/out_probe/shot")   # 확장자 제외
DELAY = float(os.environ.get("SHOT_DELAY", "25"))
S = {"t0": time.time(), "shot": False}
def L(s): unreal.log("[s1] " + str(s))
def world(): return unreal.find_object(None, LEVEL + "." + LEVEL.split("/")[-1])
def cb(dt):
    el = time.time() - S["t0"]
    if not S["shot"] and el > DELAY:
        S["shot"] = True
        unreal.SystemLibrary.execute_console_command(world(), "HighResShot 1280x720 filename=%s" % OUTPNG)
        L("shot @%.0fs -> %s" % (el, OUTPNG))
    if S["shot"] and el > DELAY + 8:
        L("quit"); unreal.SystemLibrary.execute_console_command(world(), "quit")
S["h"] = unreal.register_slate_post_tick_callback(cb)
L("등록 %s delay=%.0f" % (LEVEL, DELAY))
