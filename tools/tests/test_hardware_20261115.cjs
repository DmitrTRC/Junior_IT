const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const html = fs.readFileSync(path.join(root, 'docs/hardware-2026-11-15.html'), 'utf8');
const script = html.match(/<script id="lesson-core">([\s\S]*?)<\/script>/)[1];
const sandbox = { module: { exports: {} } };
vm.runInNewContext(script, sandbox);
const { numberForms, incrementByte, addressCapacity, bootStates, resourceComparison, volumeAnalogy, frequencyJourney } = sandbox.module.exports;

test('all byte values round-trip across binary, octal, decimal and hex', () => {
  for (let value = 0; value <= 255; value++) {
    const forms = numberForms(value);
    assert.equal(forms.binary.length, 8);
    assert.equal(forms.hex.length, 2);
    for (const [key, base] of [['binary', 2], ['octal', 8], ['decimal', 10], ['hex', 16]]) {
      assert.equal(parseInt(forms[key], base), value);
    }
  }
  assert.equal(numberForms(42).binary, '00101010');
  assert.equal(numberForms(42).octal, '52');
  assert.equal(numberForms(42).hex, '2A');
  for (const invalid of [-1, 256, 1.5, NaN, Infinity, '42']) {
    assert.throws(() => numberForms(invalid), { name: 'RangeError' });
  }
});

test('carry leaves the byte only at the unsigned 8-bit boundary', () => {
  for (let value = 0; value < 255; value++) {
    assert.equal(incrementByte(value).value, value + 1);
    assert.equal(incrementByte(value).carry, 0);
  }
  assert.equal(incrementByte(255).value, 0);
  assert.equal(incrementByte(255).carry, 1);
});

test('an address line doubles capacity; 8088 addresses 1 MiB and 286 16 MiB', () => {
  assert.equal(addressCapacity(1), 2);
  assert.equal(addressCapacity(16), 65536);
  assert.equal(addressCapacity(20), 1048576);
  assert.equal(addressCapacity(24), 16777216);
  for (let bits = 1; bits < 24; bits++) {
    assert.equal(addressCapacity(bits + 1), addressCapacity(bits) * 2);
  }
  for (const invalid of [0, 25, 2.5, NaN]) {
    assert.throws(() => addressCapacity(invalid), { name: 'RangeError' });
  }
});

test('RAM comparisons retain binary units and change with the XT configuration', () => {
  assert.equal(resourceComparison(128).phone, 98304);
  assert.equal(resourceComparison(128).pc, 262144);
  assert.equal(resourceComparison(640).phone, 19660.8);
  assert.equal(resourceComparison(640).pc, 52428.8);
  assert.equal(resourceComparison(128).phone / resourceComparison(640).phone, 5);
  for (const invalid of [0, -1, 256, '128', NaN]) {
    assert.throws(() => resourceComparison(invalid), { name: 'RangeError' });
  }
});

test('apple analogy scales volume rather than diameter by the RAM ratio', () => {
  for (const baseline of [128, 640]) {
    const volumes = volumeAnalogy(baseline);
    const ratios = resourceComparison(baseline);
    for (const kind of ['phone', 'pc']) {
      const reconstructedRatio = (volumes[kind + 'Diameter'] / 0.08) ** 3;
      assert.ok(Math.abs(reconstructedRatio / ratios[kind] - 1) < 1e-12);
    }
  }
  assert.ok(Math.abs(volumeAnalogy(128).pcDiameter - 5.12) < 1e-12);
  assert.ok(volumeAnalogy(128).phoneDiameter > 3.69);
  assert.ok(volumeAnalogy(128).phoneDiameter < 3.70);
});

test('frequency analogy converts one minute to distances on the same kilometre scale', () => {
  const finish = frequencyJourney(60);
  assert.ok(Math.abs(finish.xt - 1 / 12) < 1e-12);
  assert.ok(Math.abs(finish.phone / finish.xt - 4470 / 4.77) < 1e-10);
  assert.ok(Math.abs(finish.pc / finish.xt - 5200 / 4.77) < 1e-10);
  assert.ok(finish.phone > 78 && finish.phone < 79);
  assert.ok(finish.pc > 90 && finish.pc < 91);
  for (const key of ['xt', 'phone', 'pc']) {
    assert.equal(frequencyJourney(0)[key], 0);
    assert.equal(frequencyJourney(30)[key] * 2, finish[key]);
  }
  for (const invalid of [-1, 61, NaN, Infinity, '30']) {
    assert.throws(() => frequencyJourney(invalid), { name: 'RangeError' });
  }
});

test('boot narrative runs firmware before POST and separates OS and shell', () => {
  assert.equal(bootStates.length, 7);
  assert.match(bootStates[1].owner, /BIOS/);
  assert.match(bootStates[2].name, /POST/);
  assert.match(bootStates[3].description, /Без подходящего носителя/);
  assert.match(bootStates[4].owner, /ЗАГРУЗОЧНЫЙ/);
  assert.match(bootStates[5].owner, /ОПЕРАЦИОННОЙ/);
  assert.match(bootStates[6].name, /Оболочка/);
});

test('slide IDs and panel deep links resolve without duplicate IDs', () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
  const slideIds = [...html.matchAll(/<section class="slide[^"]*" id="([^"]+)"/g)].map(match => match[1]);
  for (const required of ['xt', 'resources', 'speed', 'same-tasks', 'lab286', 'resilience', 'upgrade', 'understanding', 'algorithm']) {
    assert.ok(slideIds.includes(required), `Missing teaching block: ${required}`);
  }
  const panel = fs.readFileSync(path.join(root, 'playground/2026-11-15/index.html'), 'utf8');
  for (const match of panel.matchAll(/hardware-2026-11-15\.html#([^"]+)/g)) {
    assert.ok(slideIds.includes(match[1]), `Missing slide: ${match[1]}`);
  }
});
