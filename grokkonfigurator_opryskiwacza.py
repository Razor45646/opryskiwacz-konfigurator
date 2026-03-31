import streamlit as st
import math
import json

st.set_page_config(
    page_title="Konfigurator Opryskiwacza Autonomicznego",
    page_icon="🌿",
    layout="wide"
)

# ═══════════════════════════════════════════════════════════════
# STYLIZACJA (bez zmian – wygląda rewelacyjnie)
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
.ok   { color: #1a7f1a; font-weight: 600; font-size: 0.95rem; }
.err  { color: #cc2200; font-weight: 600; font-size: 0.95rem; }
.warn { color: #b85c00; font-weight: 600; font-size: 0.95rem; }
.card {
    border-radius: 10px;
    padding: 14px 18px;
    margin: 6px 0;
    border-left: 5px solid #ccc;
    background: #fafafa;
    font-size: 0.9rem;
    line-height: 1.6;
}
.card.ok   { border-left-color: #1a7f1a; background: #f0faf0; }
.card.err  { border-left-color: #cc2200; background: #fff5f3; }
.card.warn { border-left-color: #b85c00; background: #fff8f0; }
.card.info { border-left-color: #1a66cc; background: #f0f5ff; }
.section { font-size: 1.05rem; font-weight: 700; margin: 1.2rem 0 0.5rem; color: #222; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# STAŁE INŻYNIERSKIE
# ═══════════════════════════════════════════════════════════════
G = 9.81
SAFETY_FACTOR = 2.0                    # współczynnik bezpieczeństwa
MIN_SHAFT_MM_FOR_HEAVY = 12
LOAD_FACTOR = 0.75                     # ile % no-load RPM osiąga przy obciążeniu
ENERGY_LOSS_MARGIN = 1.12              # +12% na straty w przewodach, DC-DC, peaki

# ═══════════════════════════════════════════════════════════════
# BAZA DANYCH (bez zmian – tylko dodano "channels" do sterowników)
# ═══════════════════════════════════════════════════════════════
MOTORS = {
    "Pololu 37D 24V 30:1 (4681) — 9 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 0.88, "rated_torque_nm": 0.22,
        "no_load_rpm": 350, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "Pololu 37D 24V 50:1 (4683) — 23 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 2.26, "rated_torque_nm": 0.57,
        "no_load_rpm": 200, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "Pololu 37D 24V 70:1 (4684) — 35 kg·cm": {
        "voltage": 24, "power_w": 20,
        "stall_torque_nm": 3.43, "rated_torque_nm": 0.86,
        "no_load_rpm": 140, "peak_current_a": 5.0, "cont_current_a": 1.5,
        "shaft_mm": 6, "qty": 4, "type": "szczotkowy"
    },
    "DC 250W szczotkowy 24V 120 RPM (1016WZ) — wózek inw.": {
        "voltage": 24, "power_w": 250,
        "stall_torque_nm": 20.0, "rated_torque_nm": 8.0,
        "no_load_rpm": 140, "peak_current_a": 35.0, "cont_current_a": 10.5,
        "shaft_mm": 17, "qty": 4, "type": "szczotkowy"
    },
    "Silnik planetarny 250W 24V 80 RPM": {
        "voltage": 24, "power_w": 250,
        "stall_torque_nm": 25.0, "rated_torque_nm": 9.5,
        "no_load_rpm": 100, "peak_current_a": 30.0, "cont_current_a": 11.0,
        "shaft_mm": 14, "qty": 4, "type": "planetarny"
    },
    "Silnik planetarny 400W 24V 100 RPM": {
        "voltage": 24, "power_w": 400,
        "stall_torque_nm": 35.0, "rated_torque_nm": 14.0,
        "no_load_rpm": 120, "peak_current_a": 45.0, "cont_current_a": 17.0,
        "shaft_mm": 16, "qty": 4, "type": "planetarny"
    },
    "Hub Motor 350W 24V (silnik w piaście)": {
        "voltage": 24, "power_w": 350,
        "stall_torque_nm": 40.0, "rated_torque_nm": 15.0,
        "no_load_rpm": 60, "peak_current_a": 40.0, "cont_current_a": 15.0,
        "shaft_mm": 20, "qty": 4, "type": "BLDC"
    },
}

CONTROLLERS = {
    "L298N — tani mostek (2A ciągłe)": {
        "max_current_a": 2.0, "voltage_max": 46,
        "channels": 2, "interface": "PWM"
    },
    "BTS7960 43A (IBT-2) — 1 kanał": {
        "max_current_a": 43.0, "voltage_max": 27,
        "channels": 1, "interface": "PWM"
    },
    "Cytron SmartDriveDuo MDDS30 — 2×30A": {
        "max_current_a": 30.0, "voltage_max": 35,
        "channels": 2, "interface": "UART/PWM/RC"
    },
    "Cytron SmartDriveDuo MDDS50 — 2×50A": {
        "max_current_a": 50.0, "voltage_max": 50,
        "channels": 2, "interface": "UART/PWM/RC"
    },
    "Sabertooth 2×32A": {
        "max_current_a": 32.0, "voltage_max": 30,
        "channels": 2, "interface": "UART/RC/analog"
    },
    "RoboClaw 2×60A": {
        "max_current_a": 60.0, "voltage_max": 34,
        "channels": 2, "interface": "UART/RC/analog"
    },
}

BATTERIES = {
    "LiFePO4 24V 20Ah (480 Wh)": {"voltage": 24, "capacity_ah": 20, "chemistry": "LiFePO4"},
    "LiFePO4 24V 40Ah (960 Wh)": {"voltage": 24, "capacity_ah": 40, "chemistry": "LiFePO4"},
    "LiFePO4 24V 60Ah (1440 Wh)": {"voltage": 24, "capacity_ah": 60, "chemistry": "LiFePO4"},
    "LiFePO4 48V 30Ah (1440 Wh)": {"voltage": 48, "capacity_ah": 30, "chemistry": "LiFePO4"},
    "LiFePO4 48V 40Ah (1920 Wh)": {"voltage": 48, "capacity_ah": 40, "chemistry": "LiFePO4"},
    "AGM 2×12V 100Ah szeregowo (24V)": {"voltage": 24, "capacity_ah": 100, "chemistry": "AGM"},
}

COMPUTERS = {
    "Raspberry Pi 5 8GB":           {"power_w": 12, "ai_capable": False},
    "NVIDIA Jetson Orin Nano 8GB":  {"power_w": 15, "ai_capable": True},
    "NVIDIA Jetson Orin NX 16GB":   {"power_w": 25, "ai_capable": True},
}

SENSORS = {
    "RPLiDAR A1 (zasięg 12m)":       {"power_w": 3.0},
    "RPLiDAR A3 (zasięg 25m)":       {"power_w": 4.5},
    "Intel RealSense D435i":          {"power_w": 4.5},
    "Luxonis OAK-D":                  {"power_w": 4.0},
    "GPS RTK Ardusimple SimpleRTK2B": {"power_w": 1.0},
}

SPRAY_PUMPS = {
    "Brak pompy":                        {"power_w": 0,   "voltage": 0},
    "Shurflo 8007 12V 8 L/min":         {"power_w": 60,  "voltage": 12},
    "Shurflo 8007 24V 8 L/min":         {"power_w": 80,  "voltage": 24},
    "Pompa membranowa 24V 15 L/min":    {"power_w": 120, "voltage": 24},
}

TERRAIN = {
    "Asfalt / twarda nawierzchnia":     0.02,
    "Trawa / miękka darń":              0.10,
    "Miękka ziemia / torf (borówka)":  0.15,
}

# ═══════════════════════════════════════════════════════════════
# FUNKCJE OBLICZENIOWE (czytelność + łatwe testowanie)
# ═══════════════════════════════════════════════════════════════
def calculate_torque_requirements(mass_kg, Cr, r_m, safety_factor, qty):
    T_req_total = mass_kg * G * Cr * r_m * safety_factor
    T_req_per_motor = T_req_total / qty
    return T_req_total, T_req_per_motor


def check_shaft_strength(mass_kg, shaft_mm):
    if mass_kg > 80 and shaft_mm < MIN_SHAFT_MM_FOR_HEAVY:
        return True, "RYZYKO MECHANICZNEGO ŚCIĘCIA WAŁU"
    return False, "WAŁ OK"


def calculate_energy_balance(motor, qty, extra_w, batt, route_time_h):
    motor_cont_a = motor["cont_current_a"] * qty
    extra_a = extra_w / batt["voltage"] if batt["voltage"] > 0 else 0
    total_a = motor_cont_a + extra_a
    total_w = total_a * batt["voltage"]
    runtime_h = (batt["capacity_ah"] / total_a) / ENERGY_LOSS_MARGIN if total_a > 0 else 0
    runtime_ok = runtime_h >= route_time_h
    return total_a, total_w, runtime_h, runtime_ok


# ═══════════════════════════════════════════════════════════════
# INTERFEJS
# ═══════════════════════════════════════════════════════════════
st.title("🌿 Konfigurator Autonomicznego Opryskiwacza Polowego")
st.caption("Walidacja fizyczna i elektryczna • wzory inżynierskie • wersja ulepszona")
st.markdown("---")

col_left, col_mid, col_right = st.columns([1.0, 1.3, 1.7])

# ── LEWY + ŚRODKOWY PANEL (live update – obliczenia są lekkie)
with col_left:
    st.markdown("### ⚙️ Parametry fizyczne")
    total_mass_kg = st.slider("Masa całkowita pojazdu (kg)", 20, 350, 145, 5,
                              help="Rama + akumulator + elektronika + zbiornik z cieczą")
    wheel_diameter_mm = st.slider("Średnica koła (mm)", 150, 600, 254, 5)
    terrain_choice = st.selectbox("Typ terenu", list(TERRAIN.keys()), index=2)
    Cr = TERRAIN[terrain_choice]
    r_m = (wheel_diameter_mm / 2) / 1000.0
    st.info(f"**Cr = {Cr}** | **r = {r_m*1000:.0f} mm**")

    st.markdown("---")
    st.markdown("### 💧 Parametry pola")
    tank_vol = st.slider("Pojemność zbiornika (L)", 0, 200, 100, 10)
    row_len_m = st.slider("Długość rzędu (m)", 10, 400, 180, 10)
    num_rows = st.number_input("Liczba rzędów", 1, 100, 21, 1)
    total_route_m = num_rows * row_len_m
    st.caption(f"Masa cieczy: ~{tank_vol} kg | Łączna trasa: **{total_route_m} m**")

with col_mid:
    st.markdown("### 🔩 Napęd")
    motor_choice = st.selectbox("Silnik (×4 sztuki)", list(MOTORS.keys()))
    motor = MOTORS[motor_choice]
    ctrl_choice = st.selectbox("Sterownik silników", list(CONTROLLERS.keys()))
    ctrl = CONTROLLERS[ctrl_choice]

    st.markdown("### 🔋 Zasilanie")
    batt_choice = st.selectbox("Akumulator", list(BATTERIES.keys()))
    batt = BATTERIES[batt_choice]

    st.markdown("### 🖥️ Elektronika")
    comp_choice = st.selectbox("Komputer główny", list(COMPUTERS.keys()))
    comp = COMPUTERS[comp_choice]
    sensor_choice = st.selectbox("Sensor / LiDAR", list(SENSORS.keys()))
    sensor = SENSORS[sensor_choice]
    gps_on = st.checkbox("GPS RTK Ardusimple (+1 W)", value=True)
    imu_on = st.checkbox("IMU BNO085 (+0.3 W)", value=True)
    router_on = st.checkbox("Router WiFi 5 GHz (+8 W)", value=True)

    st.markdown("### 🚿 Moduł oprysku")
    pump_choice = st.selectbox("Pompa opryskiwacza", list(SPRAY_PUMPS.keys()))
    pump = SPRAY_PUMPS[pump_choice]
    nozzle_count = st.number_input("Liczba dysz", 1, 20, 10, 1)

# ═══════════════════════════════════════════════════════════════
# OBLICZENIA (wywołanie funkcji)
# ═══════════════════════════════════════════════════════════════
T_req_total, T_req_per_motor = calculate_torque_requirements(
    total_mass_kg, Cr, r_m, SAFETY_FACTOR, motor["qty"]
)
T_avail_total = motor["stall_torque_nm"] * motor["qty"]
torque_ok = T_avail_total >= T_req_total
reserve_percent = ((T_avail_total / T_req_total) - 1) * 100 if T_req_total > 0 else 0

shaft_risk, shaft_msg = check_shaft_strength(total_mass_kg, motor["shaft_mm"])

voltage_ok = (batt["voltage"] == motor["voltage"])

# Sterownik – ulepszona logika
channels_per_ctrl = ctrl["channels"]
motors_per_ctrl = channels_per_ctrl  # zakładamy 1 silnik na kanał
num_controllers_needed = math.ceil(motor["qty"] / motors_per_ctrl)
ctrl_current_ok = ctrl["max_current_a"] >= motor["peak_current_a"]
ctrl_voltage_ok = ctrl["voltage_max"] >= batt["voltage"]
controller_ok = ctrl_current_ok and ctrl_voltage_ok

# Bilans energetyczny
extra_w = (
    comp["power_w"] +
    sensor["power_w"] +
    (1.0 if gps_on else 0) +
    (0.3 if imu_on else 0) +
    (8.0 if router_on else 0) +
    pump["power_w"]
)
total_a, total_w, runtime_h, runtime_ok = calculate_energy_balance(
    motor, motor["qty"], extra_w, batt, 0
)

# Prędkość (z obciążeniem)
v_ms = (motor["no_load_rpm"] * 2 * math.pi * r_m) / 60.0
v_ms_real = v_ms * LOAD_FACTOR
v_kmh = v_ms_real * 3.6
route_time_h = (total_route_m / (v_ms_real * 3600)) if v_ms_real > 0 else 0
runtime_ok = runtime_h >= route_time_h

pump_ok = (pump["voltage"] == 0 or pump["voltage"] <= batt["voltage"])

# ═══════════════════════════════════════════════════════════════
# PRAWY PANEL – RAPORT KOMPATYBILNOŚCI
# ═══════════════════════════════════════════════════════════════
with col_right:
    st.markdown("### 📋 Dynamiczny Raport Kompatybilności")

    # 1. Moment obrotowy
    st.markdown('<div class="section">1. Moment obrotowy  T = (m · g · f · r) · S</div>', unsafe_allow_html=True)
    formula = f"T = ({total_mass_kg} · {G} · {Cr} · {r_m:.3f}) · {SAFETY_FACTOR} = <b>{T_req_total:.2f} Nm</b>"
    avail = f"Dostępne: {motor['stall_torque_nm']:.2f} Nm/sil × {motor['qty']} = <b>{T_avail_total:.2f} Nm</b>"
    if torque_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>MOMENT OK</b><br>{formula}<br>{avail}<br>'
            f'Na silnik: {T_req_per_motor:.2f} Nm | Rezerwa: <b>{reserve_percent:.0f}%</b></div>',
            unsafe_allow_html=True)
    else:
        deficit = T_req_total - T_avail_total
        st.markdown(
            f'<div class="card err">❌ <b>NIEWYSTARCZAJĄCY MOMENT</b><br>{formula}<br>{avail}<br>'
            f'Brakuje: <b>{deficit:.2f} Nm</b> – wybierz silnik o wyższym Stall Torque.</div>',
            unsafe_allow_html=True)

    # 2. Wytrzymałość wału
    st.markdown('<div class="section">2. Wytrzymałość wału silnika</div>', unsafe_allow_html=True)
    if shaft_risk:
        st.markdown(
            f'<div class="card err">⚠️ <b>{shaft_msg}</b><br>'
            f'Masa {total_mass_kg} kg &gt; 80 kg AND wał {motor["shaft_mm"]} mm &lt; {MIN_SHAFT_MM_FOR_HEAVY} mm.<br>'
            f'Rozwiązanie: silnik z wałem ≥ 12 mm lub napęd łańcuchowy/pasowy.</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card ok">✅ <b>{shaft_msg}</b> — Masa {total_mass_kg} kg, '
            f'wał {motor["shaft_mm"]} mm – montaż bezpośredni dopuszczalny.</div>',
            unsafe_allow_html=True)

    # 3. Napięcie
    st.markdown('<div class="section">3. Kompatybilność napięciowa</div>', unsafe_allow_html=True)
    if voltage_ok:
        st.markdown(f'<div class="card ok">✅ <b>NAPIĘCIE OK</b> — {batt["voltage"]} V = {motor["voltage"]} V</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA</b> — '
            f'Akumulator {batt["voltage"]} V ≠ Silnik {motor["voltage"]} V</div>',
            unsafe_allow_html=True)

    # 4. Sterownik (ulepszona logika)
    st.markdown('<div class="section">4. Sterownik silników</div>', unsafe_allow_html=True)
    if not ctrl_voltage_ok:
        st.markdown(f'<div class="card err">❌ <b>NAPIĘCIE STEROWNIKA ZA NISKIE</b> — Max {ctrl["voltage_max"]} V &lt; {batt["voltage"]} V</div>', unsafe_allow_html=True)
    elif ctrl_current_ok:
        st.markdown(
            f'<div class="card ok">✅ <b>STEROWNIK OK</b><br>'
            f'Peak silnika {motor["peak_current_a"]} A ≤ Max sterownika {ctrl["max_current_a"]} A<br>'
            f'Potrzebna liczba sterowników: <b>{num_controllers_needed}</b> szt.<br>'
            f'Interfejs: {ctrl["interface"]}</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="card err">❌ <b>STEROWNIK ZA SŁABY</b> — '
            f'Peak silnika {motor["peak_current_a"]} A &gt; {ctrl["max_current_a"]} A</div>',
            unsafe_allow_html=True)

    # 5. Bilans energetyczny
    st.markdown('<div class="section">5. Bilans energetyczny  t = C_ah / I_total</div>', unsafe_allow_html=True)
    ecls = "ok" if runtime_ok else "err"
    eicon = "✅" if runtime_ok else "❌"
    elabel = "WYSTARCZAJĄCY" if runtime_ok else "NIEWYSTARCZAJĄCY"
    st.markdown(
        f'<div class="card {ecls}">{eicon} <b>CZAS PRACY — {elabel}</b><br>'
        f'Prąd silników (ciągły): {motor["cont_current_a"]*motor["qty"]:.1f} A<br>'
        f'Elektronika + pompa: {extra_w:.0f} W → {extra_w/batt["voltage"]:.1f} A<br>'
        f'Łączny pobór: <b>{total_a:.1f} A</b> ({total_w:.0f} W)<br>'
        f'Czas pracy: <b>{runtime_h:.1f} h</b> | Czas przejazdu pola: <b>{route_time_h:.2f} h</b></div>',
        unsafe_allow_html=True)

    # 6. Prędkość robota
    st.markdown('<div class="section">6. Prędkość robota</div>', unsafe_allow_html=True)
    speed_ok = 0.5 <= v_kmh <= 4.0
    scls = "ok" if speed_ok else "warn"
    snote = " (optymalna 1–3 km/h)" if v_kmh > 4.0 else (" (za wolno)" if v_kmh < 0.5 else "")
    st.markdown(
        f'<div class="card {scls}">{"✅" if speed_ok else "⚠️"} <b>Prędkość robocza: {v_kmh:.2f} km/h</b>{snote}<br>'
        f'RPM no-load: {motor["no_load_rpm"]} | Obciążenie: {LOAD_FACTOR*100:.0f}%</div>',
        unsafe_allow_html=True)

    # 7. Pompa
    if pump["voltage"] > 0:
        st.markdown('<div class="section">7. Moduł oprysku</div>', unsafe_allow_html=True)
        if pump_ok:
            st.markdown(
                f'<div class="card ok">✅ <b>POMPA OK</b> — {pump_choice}<br>'
                f'Napięcie: {pump["voltage"]} V | Pobór: {pump["power_w"]} W</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card err">❌ <b>NIEZGODNOŚĆ NAPIĘCIA POMPY</b></div>', unsafe_allow_html=True)

    # ── PODSUMOWANIE + EKSPORT
    st.markdown("---")
    checks = [torque_ok, not shaft_risk, voltage_ok, ctrl_current_ok, ctrl_voltage_ok, runtime_ok, pump_ok]
    passed = sum(checks)
    total = len(checks)
    pct = int(passed / total * 100)

    if pct == 100:
        st.success(f"✅ **Wszystko OK** ({pct}%) – konfiguracja gotowa do uruchomienia!")
    elif pct >= 70:
        st.warning(f"⚠️ {passed}/{total} sprawdzeń OK ({pct}%) – popraw drobne błędy")
    else:
        st.error(f"❌ {passed}/{total} sprawdzeń OK ({pct}%) – wymaga korekty")

    # Eksport konfiguracji
    config = {
        "motor": motor_choice,
        "controller": ctrl_choice,
        "controllers_needed": num_controllers_needed,
        "battery": batt_choice,
        "terrain": terrain_choice,
        "mass_kg": total_mass_kg,
        "wheel_diameter_mm": wheel_diameter_mm,
        "torque_reserve_percent": round(reserve_percent, 1),
        "runtime_hours": round(runtime_h, 2),
        "speed_kmh": round(v_kmh, 2),
        "status": "OK" if pct == 100 else "Needs fixes"
    }

    st.download_button(
        label="📤 Pobierz konfigurację jako JSON",
        data=json.dumps(config, indent=2, ensure_ascii=False),
        file_name="opryskiwacz_config.json",
        mime="application/json",
        use_container_width=True
    )

    st.caption("Wzory: T=(m·g·f·r)·S | t=C/I | V=(RPM·2π·r)/60 | S=2.0")