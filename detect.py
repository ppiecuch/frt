import os, sys, errno
import subprocess


import version
import methods

if version.major > 2:
    yes = True
    no = False
else:
    yes = "yes"
    no = "no"

sysroot = os.environ["SYSROOT"] if "SYSROOT" in os.environ else ""
pkgenvstr = ""
if sysroot:
    pkgenvstr = (
        "PKG_CONFIG_DIR= PKG_CONFIG_PATH= PKG_CONFIG_LIBDIR="
        + sysroot
        + "/usr/share/pkgconfig:"
        + sysroot
        + "/opt/vc/lib/pkgconfig"
        + " "
    )


def is_active():

    return True


def get_name():

    return "FRT"


def can_build():

    if os.name != "posix":
        return False
    return True


def get_opts():

    return [
        ("frt_arch", "Architecture (pc/pi1/pi2/pi3/pi4/gcw0/*)", "pc"),
        ("use_llvm", "Use llvm compiler", no),
        ("use_lto", "Use link time optimization", no),
    ]


def get_flags():

    return [
        ("tools", no),
    ]


def check(env, key):

    if not (key in env):
        return False
    if version.major > 2:
        return env[key]
    else:
        return env[key] == "yes"


def checkexe(exe):

    try:
        subprocess.call(exe)
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False
    return True

def checkcfg(env, cmd):

        env.ParseConfig("%s %s" % (pkgenvstr, cmd))


def configure(env):

    import methods

    env.Append(CPPPATH=["#platform/frt"])

    if check(env, "use_llvm"):
        if "clang++" not in env["CXX"]:
            env["CC"] = "clang"
            env["CXX"] = "clang++"
            env["LD"] = "clang++"
        env.Append(CPPFLAGS=["-DTYPED_METHOD_BIND"])
        env.extra_suffix = ".llvm"

    if check(env, "use_lto"):
        if check(env, "use_llvm"):
            env.Append(CCFLAGS=["-flto=thin"])
            env.Append(LINKFLAGS=["-fuse-ld=lld", "-flto=thin"])
            env["AR"] = "llvm-ar"
            env["RANLIB"] = "llvm-ranlib"
        else:
            env.Append(CCFLAGS=["-flto"])
            env.Append(LINKFLAGS=["-flto"])

    env.Append(CCFLAGS=["-pipe"])
    env.Append(LINKFLAGS=["-pipe"])

    if os.system(pkgenvstr + "pkg-config --exists alsa") == 0:
        print("Enabling ALSA")
        env.Append(CPPFLAGS=["-DALSA_ENABLED"])
        checkcfg(env, "pkg-config alsa --cflags --libs")
    else:
        print("ALSA libraries not found, disabling driver")

    # common
    if not check(env, "builtin_freetype"):
        checkcfg(env, "pkg-config freetype2 --cflags --libs")
    if not check(env, "builtin_libpng"):
        checkcfg(env, "pkg-config libpng --cflags --libs")
    if not check(env, "builtin_zlib"):
        checkcfg(env, "pkg-config zlib --cflags --libs")
    if not check(env, "builtin_libwebp"):
        checkcfg(env, "pkg-config libwebp --cflags --libs")
    if not check(env, "builtin_libtheora"):
        checkcfg(env, "pkg-config theora theoradec --cflags --libs")
    if not check(env, "builtin_libvorbis"):
        checkcfg(env, "pkg-config vorbis vorbisfile --cflags --libs")
    if not check(env, "builtin_opus"):
        checkcfg(env, "pkg-config opus opusfile --cflags --libs")
    if not check(env, "builtin_libogg"):
        checkcfg(env, "pkg-config ogg --cflags --libs")
    # 2.1 / 3.0
    if version.major == 2 or (version.major == 3 and version.minor == 0):
        if not check(env, "builtin_openssl") and check(env, "module_openssl_enabled"):
            checkcfg(env, "pkg-config openssl --cflags --libs")
    # 3.0+
    if version.major == 3:
        if not check(env, "builtin_libvpx"):
            checkcfg(env, "pkg-config vpx --cflags --libs")
        if not check(env, "builtin_bullet"):
            checkcfg(env, "pkg-config bullet --cflags --libs")
        if not check(env, "builtin_enet"):
            checkcfg(env, "pkg-config libenet --cflags --libs")
        if not check(env, "builtin_zstd"):
            checkcfg(env, "pkg-config libzstd --cflags --libs")
        if not check(env, "builtin_pcre2"):
            checkcfg(env, "pkg-config libpcre2-32 --cflags --libs")
    # 3.1+
    if version.major == 3 and version.minor >= 1:
        if not check(env, "builtin_mbedtls") and check(env, "module_openssl_enabled"):
            env.Append(LIBS=["mbedtls", "mbedcrypto", "mbedx509"])
        if not check(env, "builtin_wslay") and check(env, "module_openssl_enabled"):
            checkcfg(env, "pkg-config libwslay --cflags --libs")
        if not check(env, "builtin_miniupnpc"):
            env.Prepend(CPPPATH=[sysroot + "/usr/include/miniupnpc"])
            env.Append(LIBS=["miniupnpc"])

    # pkg-config returns 0 when the lib exists...
    found_udev = not os.system(pkgenvstr + "pkg-config --exists libudev")
    if found_udev:
        print("Enabling udev support")
        env.Append(CPPFLAGS=["-DUDEV_ENABLED"])
        checkcfg(env, "pkg-config libudev --cflags --libs")
        env.Append(CPPFLAGS=["-DJOYDEV_ENABLED"])
        if version.major > 2:
            env.Append(FRT_MODULES=["import/joypad_linux.cpp"])
        else:
            env.Append(FRT_MODULES=["import/joystick_linux.cpp"])
    else:
        print("libudev development libraries not found, disabling udev support")

    if version.major == 2:
        if version.minor == 1 and version.patch >= 4:
            gen_suffix = "glsl.gen.h"
        else:
            gen_suffix = "glsl.h"
        env.Append(
            BUILDERS={
                "GLSL120": env.Builder(action=methods.build_legacygl_headers, suffix=gen_suffix, src_suffix=".glsl")
            }
        )
        env.Append(
            BUILDERS={"GLSL": env.Builder(action=methods.build_glsl_headers, suffix=gen_suffix, src_suffix=".glsl")}
        )
        env.Append(
            BUILDERS={
                "GLSL120GLES": env.Builder(action=methods.build_gles2_headers, suffix=gen_suffix, src_suffix=".glsl")
            }
        )

    if checkexe(["arm-linux-gnueabihf-gcc", "--version"]):
        print("*** Using arm-linux-gnueabihf toolchain by default.")
        env["CC"] = "arm-linux-gnueabihf-gcc"
        env["CXX"] = "arm-linux-gnueabihf-g++"
        env["LD"] = "arm-linux-gnueabihf-g++"
        env["AR"] = "arm-linux-gnueabihf-ar"
        env["STRIP"] = "arm-linux-gnueabihf-strip"

    # cleanup some false-positives warnings of gcc 4.8/4.9
    env.Append(CCFLAGS=["-fno-strict-aliasing", "-fno-strict-overflow"])
    env.Append(CXXFLAGS=["-Wno-class-memaccess", "-Wno-sign-compare"])

    if env["frt_arch"] == "pi1" or env["frt_arch"] == "piz":
        env.Append(CCFLAGS=["-mcpu=arm1176jzf-s", "-mfpu=vfp"])
        env.extra_suffix += ".pi1"
    elif env["frt_arch"] == "pi2":
        env.Append(CCFLAGS=["-mcpu=cortex-a7", "-mfpu=neon-vfpv4"])
        env.extra_suffix += ".pi2"
    elif env["frt_arch"] == "pi3":
        env.Append(CCFLAGS=["-mcpu=cortex-a53", "-mfpu=neon-fp-armv8"])
        env.extra_suffix += ".pi3"
    elif env["frt_arch"] == "pi4":
        env.Append(CCFLAGS=["-mcpu=cortex-a72", "-mfpu=neon-fp-armv8", "-mtune=cortex-a72"])
        env.extra_suffix += ".pi4"
    elif env["frt_arch"] == "gcw0":
        env.Append(CPPDEFINES=["__GCW0__", "PTHREAD_NO_RENAME"])
        # for building only
        env.Append(CPPPATH=["#platform/frt/bits/Xorg"])
        if not checkexe(["mipsel-linux-gcc", "--version"]):
           print("*** Cannot find mipsel-linux toolchain.")
        env["CC"] = "mipsel-linux-gcc"
        env["CXX"] = "mipsel-linux-g++"
        env["LD"] = "mipsel-linux-g++"
        env["AR"] = "mipsel-linux-ar"
        env["STRIP"] = "mipsel-linux-strip"
        env["arch"] = "mipsel"
        env.extra_suffix += ".gcw0"
    elif env["frt_arch"] != "pc":
        env.extra_suffix += "." + env["frt_arch"]

    if env["frt_arch"].startswith("pi"):
        env.Append(CCFLAGS=["-mfloat-abi=hard", "-mlittle-endian", "-munaligned-access"])
        env.Append(CPPDEFINES=["_rpi_"])
        env.Append(LIBS=["rt"])
        env["arch"] = "arm"

    if sysroot:
        env.Append(CCFLAGS=["--sysroot=" + sysroot])

    opt = "-O3"
    if methods.using_gcc(env):
        # gcc 10.2 for mips crash for -O3
        ver = methods.get_compiler_version(env) or [-1, -1]
        if ver[0] == 10 and ver[1] == 2 and env["arch"].startswith("mips"):
            print("Warning: -O2 is selected for release build optimization.")
            opt = "-O2"
    if env["target"] == "release":
        env.Append(CCFLAGS=[opt, "-fomit-frame-pointer"])
    elif env["target"] == "release_debug":
        env.Append(CCFLAGS=[opt, "-DDEBUG_ENABLED"])
    elif env["target"] == "debug":
        env.Append(CCFLAGS=["-g2", "-DDEBUG_ENABLED", "-DDEBUG_MEMORY_ENABLED"])
    if env["target"].startswith("release"):
        if version.major == 2 or (version.major == 3 and version.minor == 0):
            env.Append(CCFLAGS=["-ffast-math"])

    env.Append(CPPFLAGS=["-DFRT_ENABLED", "-DUNIX_ENABLED", "-DGLES2_ENABLED", "-DGLES_ENABLED"])
    env.Append(LIBS=["pthread"])

    env.Append(FRT_MODULES=["envprobe.cpp", "envcompatibility.cpp"])
    env.Append(FRT_MODULES=["video_fbdev.cpp", "keyboard_linux_input.cpp", "mouse_linux_input.cpp"])
    env.Append(FRT_MODULES=["video_x11.cpp", "keyboard_x11.cpp", "mouse_x11.cpp"])
    if version.major >= 3:
        env.Append(FRT_MODULES=["import/key_mapping_x11_3.cpp"])
    else:
        env.Append(FRT_MODULES=["import/key_mapping_x11_2.cpp"])
    env.Append(FRT_MODULES=["dl/x11.gen.cpp", "dl/egl.gen.cpp"])
    if os.path.isfile(sysroot + "/opt/vc/include/bcm_host.h"):
        env.Append(FRT_MODULES=["video_bcm.cpp", "dl/bcm.gen.cpp"])
        env.Append(CCFLAGS=["-I%s/opt/vc/include" % sysroot])
    if os.path.isfile(sysroot + "/usr/include/gbm.h"):
        env.Append(FRT_MODULES=["video_kmsdrm.cpp", "dl/gbm.gen.cpp", "dl/drm.gen.cpp"])
    env.Append(FRT_MODULES=["dl/gles2.gen.cpp"])
    if version.major >= 3:
        env.Append(FRT_MODULES=["dl/gles3.gen.cpp"])
    env.Append(LIBS=["dl"])
