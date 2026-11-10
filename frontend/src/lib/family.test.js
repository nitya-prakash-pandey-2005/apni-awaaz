// npm test
import test from "node:test";
import assert from "node:assert/strict";
import { mapsLink, normPhone, smsLink, sosMessage, waLink } from "./family.js";

test("phone numbers are normalised to digits with the country code", () => {
  assert.equal(normPhone("98765 43210"), "919876543210");
  assert.equal(normPhone("+91-98765-43210"), "919876543210");
  assert.equal(normPhone("098765 43210"), "919876543210");
  assert.equal(normPhone("12345"), "");
  assert.equal(normPhone(""), "");
});

test("message in the person's language, with or without a location", () => {
  const loc = { lat: 12.971599, lng: 77.594566 };
  assert.equal(mapsLink(loc), "https://maps.google.com/?q=12.97160,77.59457");
  assert.match(sosMessage("hi-IN", loc), /^आपातकाल! .*\nमेरी लोकेशन: https:\/\/maps\.google\.com\/\?q=12\.97160,77\.59457$/u);
  assert.match(sosMessage("ta-IN", null), /^அவசரம்! .*\n\(இருப்பிடம் கிடைக்கவில்லை.\)$/u);
  assert.match(sosMessage("te-IN", null), /^Emergency! /);  // other languages: English
});

test("WhatsApp and SMS links carry the encoded message", () => {
  const text = "Help me\nnow & here";
  assert.equal(waLink("9876543210", text), "https://wa.me/919876543210?text=Help%20me%0Anow%20%26%20here");
  assert.equal(smsLink("9876543210", text), "sms:+919876543210?&body=Help%20me%0Anow%20%26%20here");
});
