/*---------- Local LAN API (Home Assistant) ------------*/
let HA_SP_MIN = 30;
let HA_SP_MAX = 72;

let heaterState = function() {
  return {
    temperature: device.temperature,
    setpoint: device.setpoint,
    heating: sm.machineState === sm.HEAT,
    machine_state: sm.machineState,
    error: device.temperature === -1,
    ready: device.temperature !== 120,
    min_setpoint: HA_SP_MIN,
    max_setpoint: HA_SP_MAX,
    schedules: device.schedules
  };
};

RPC.addHandler('Heater.Get', function(args) {
  return heaterState();
});

RPC.addHandler('Heater.Set', function(args) {
  if (typeof(args) !== 'object' || typeof(args.setpoint) !== 'number') {
    return {error: -1, message: 'Bad request. Expected: {"setpoint":number}'};
  }
  let sp = Math.round(args.setpoint);
  if (sp !== 0 && (sp < HA_SP_MIN || sp > HA_SP_MAX)) {
    return {error: -1, message: 'setpoint must be 0 (off) or ' + JSON.stringify(HA_SP_MIN) + '..' + JSON.stringify(HA_SP_MAX)};
  }
  if (device.temperature === -1) {
    return {error: -1, message: 'heater sensor error'};
  }
  device.setpoint = sp;
  sm.evhandler(sm.SETPOINT_CHANGE);
  return heaterState();
});