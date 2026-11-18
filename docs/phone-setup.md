# Setting up your phone

This guide assumes you've never touched these settings before. It takes about five minutes, and you only do it once per phone.

**Why is this needed?** Android only lets a computer see and control the screen if you've switched on a hidden switch called **USB debugging**. It lives in a hidden menu called **Developer options**, which you unlock first. Nothing is installed on the phone, and you can switch it all off again at any time ([see the end](#turning-it-off-again)).

> Menu names differ a little between phone brands. The steps use the names from Google Pixel phones and give the usual names for other brands. If you can't find something, type its name (for example *Build number*) into the search box at the top of the phone's Settings app.

---

## Step 1: Unlock "Developer options"

1. Open the **Settings** app on your phone.
2. Scroll all the way down and tap **About phone**.
   - Samsung: **About phone → Software information**
   - Xiaomi / Redmi / POCO: **About phone**
   - OnePlus / OPPO / Realme: **About device → Version**
3. Find **Build number**.
   - Xiaomi: **MIUI version** or **OS version**
4. **Tap it 7 times quickly.** After a few taps the phone counts down (*"You are now 3 steps away from being a developer"*).
5. If the phone asks for your PIN, pattern or password, enter it.
6. You'll see **"You are now a developer!"** Developer options are now unlocked.

## Step 2: Turn on "USB debugging"

1. Go back to the main **Settings** screen.
2. Open **System → Developer options**.
   - Samsung: **Developer options** is near the bottom of the main Settings list
   - Xiaomi: **Additional settings → Developer options**
   - OnePlus / OPPO / Realme: **System settings → Developer options**
3. Scroll down to **USB debugging** and turn it **on**.
4. Confirm the warning by tapping **OK**.

> **Xiaomi, Redmi, POCO:** also turn on **USB debugging (Security settings)** if it's there. Without it, you can see the screen but not tap or type. Xiaomi may ask you to sign in to a Mi account first.

## Step 3: Connect the phone to your computer

1. Make sure scrcpy-autolaunch is running: its icon <img src="images/tray-waiting.png" width="18" alt=""> is in the tray, near the clock.
2. **Unlock your phone**, then plug it in with a USB cable.
   - Use a cable that can carry data. Some cheap cables only charge; if nothing happens, try another cable.
3. The phone asks **"Allow USB debugging?"** and shows a long code (the computer's "fingerprint").
   - Tick **"Always allow from this computer"**, so it doesn't ask every time.
   - Tap **Allow**.
4. A few seconds later, **your phone's screen opens in a window on your computer.** You can use the mouse and keyboard to control it.

That's it. From now on, plugging in the phone opens the window by itself.

### If the window doesn't open

| What you see | What to do |
|---|---|
| No "Allow USB debugging?" question on the phone | Unplug, unlock the phone, plug in again. Check that USB debugging is still on (step 2). Try another cable or USB port |
| The tray menu says *"allow USB debugging on the phone"* | The question is waiting on the phone: unlock it and tap **Allow** |
| A notification like *"Charging this device via USB"* and nothing else | Fine for most phones. If it still doesn't work, tap the notification and choose **File transfer** |
| The computer makes the "device connected" sound, but nothing opens | USB debugging is probably off: see step 2 |
| The window opens, but you can't tap or type (Xiaomi) | Turn on **USB debugging (Security settings)** (step 2) |

`scrcpy-autolaunch doctor` (in a terminal) checks everything and tells you what's missing. There's more in [troubleshooting.md](troubleshooting.md).

---

## Optional: use it without a cable (Wi-Fi)

This needs **Android 11 or newer**, and the phone and the computer must be on the **same Wi-Fi network**.

1. On the phone, open **Settings → System → Developer options** (as in step 2).
2. Tap the words **Wireless debugging** (not just the switch), turn it **on**, and confirm with **Allow**.
3. On the computer, click the tray icon, then **Wi-Fi → Pair new phone…**. A small window opens.
4. On the phone, tap **Pair device with pairing code**. It shows:
   - a **Wi-Fi pairing code** (6 digits), and
   - an **IP address & Port**, for example `192.168.1.132:41234`.
5. Type both into the window on the computer, then click **Pair**.
6. Done. The phone now appears at the top of the tray menu. Click it to open its screen over Wi-Fi.

Good to know:
- The phone turns **Wireless debugging** off by itself after a restart, or when you join another network. Just switch it on again (step 2 above); you don't need to pair again.
- Wi-Fi mirroring uses more battery than USB, because the phone isn't charging.

More details: [wifi.md](wifi.md).

---

## Turning it off again

Everything above can be undone:
- **Stop one computer's access:** *Developer options → Revoke USB debugging authorizations*. Every computer has to ask again.
- **Stop everything:** turn off **USB debugging** and **Wireless debugging**, or turn off **Developer options** completely with the switch at the top of that screen.

## Is this safe?

USB debugging lets a computer you've allowed control the phone, which is exactly what this app needs. A few habits keep it safe:
- Only tap **Allow** for **your own** computer. If an unknown computer or a public charging station asks, tap **Deny**.
- If you lose a computer you've allowed, use **Revoke USB debugging authorizations** (above).
- Banking and payment apps may warn about developer options, or refuse to open while they're on. If that bothers you, turn Developer options off when you don't need mirroring.
