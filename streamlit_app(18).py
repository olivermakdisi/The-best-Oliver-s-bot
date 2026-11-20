# Optional permanent storage (Supabase): run once in the SQL editor
#   create table kv (key text primary key, value jsonb);
# then add SUPABASE_URL and SUPABASE_KEY to the app Secrets.
# Without it the state is kept in state.json (lost on reboot/redeploy).
# Market data: Yahoo Finance forex 5m candles (query1, then query2). Strategies: break & retest + breakout.
# All times are UTC.
import hashlib
import html
import json
import secrets
import smtplib
import threading
import time
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.message import EmailMessage

import streamlit as st

st.set_page_config(page_title="Forex Signals", layout="centered")

st.markdown(
    "<style>.stApp{background:#000}#MainMenu{visibility:hidden}footer{visibility:hidden}"
    "header{visibility:hidden}.block-container{padding:1rem;max-width:520px}"
    ".stApp label,.stApp p,.stApp h1,.stApp h2,.stApp h3,.stApp .stMarkdown{color:#00e676 !important}"
    ".msg{direction:ltr;text-align:left;background:#0a0a0a;border:1px solid #1b5e20;border-radius:14px;"
    "padding:12px 14px;margin:10px 0;font-size:17px;line-height:1.6;color:#00e676}"
    ".msg .t{display:block;text-align:right;font-size:12px;color:#2e7d32}"
    ".sig{border:2px solid #00e676}"
    ".wait{text-align:center;direction:rtl;color:#2e7d32}"
    ".res{display:inline-block;padding:0 8px;border-radius:6px;font-weight:bold}"
    ".WIN{background:#00e676;color:#000}"
    ".LOSS{background:#000;color:#00e676;border:1px solid #00e676}"
    ".DRAW{background:#1b5e20;color:#000}"
    ".sum{direction:ltr;text-align:center;background:#0a0a0a;border:1px solid #00e676;"
    "border-radius:14px;padding:12px;margin:10px 0;font-size:16px;color:#00e676}"
    ".sum b{font-size:28px;display:block}"
    ".sum span{color:#2e7d32;font-size:13px}"
    "</style>",
    unsafe_allow_html=True,
)

OWNER_EMAIL = "olivermakdisi12@gmail.com"
PRICE = 500
PAY_URL = ""  # paste your Stripe / PayPal / Gumroad payment link here
CODE_HASHES = {
    "2f649ad5812f90a8ac34",
    "51b4284c95aa69e54814",
    "d5b974a952cb8e7cb567",
    "c378a536ebd10077dd92",
    "491be7c9a6054d1ee4a5",
    "67e85a23a4768c6176e7",
    "110961a065c325d51fcc",
    "04f7b24975efefa3d381",
    "3d54973bd01ccbdc3a35",
    "3060259f29cb561bea55",
    "a1a344f9eecc377202a2",
    "afced2fdacac0b5b900c",
    "3f95f9b7a42b078b4f37",
    "84f491b0d20a5431e157",
    "37ad598ff91dd2af5bd9",
    "df7890794ca4052df038",
    "db79c4abd3781b73aaf7",
    "68ec62712c45e73bec74",
    "f28d5e0d500bb7ec7c0d",
    "a52d4fb4b63537d4eef9",
    "698e2384d3143b0d7a67",
    "8a29afd38f0d1b4ecac1",
    "81d64c2efefce0944538",
    "cffa7d945543a1300789",
    "a439372e2c15891cf071",
    "56e8222ffadff6db96b5",
    "849a2891e74f7a74d91f",
    "c2570f4fca48290f93ca",
    "d9da8c31afd3bc578020",
    "4e1716d91eea02fa5ca0",
    "c5a0e43beab625fefc1a",
    "22fb877f94a6e9baf4d9",
    "809b75d01bab16d6b6f1",
    "b00609754beb59a4defe",
    "f1aba4f7a61f7961117f",
    "3ed89a09f56f2c8d7f50",
    "646b065a42ffac536176",
    "0b46dcb524ad05590498",
    "23fe7158a392e48672f9",
    "1e58b8a19155cf5fbf15",
    "c166762039bc772bef53",
    "3e8c84e9ab742e7a9245",
    "6329f2a567bc21bc04bd",
    "81120e8c74ad45f15c83",
    "9877e74a5a20d7d34bb5",
    "b2b6804538d150a4bdf8",
    "792caaefbd9e2c614d05",
    "d1b3038e521b099682a8",
    "10c59f9a8c529c502bdd",
    "be53a546a0e04a21344d",
    "2ba8187a0c09b850ecfe",
    "a1c5363b8591b26d8982",
    "e143ef5e207d8a40f374",
    "81d10870c1e2a39bcb64",
    "987824cad8b8a8738934",
    "6166ecde05fe134c840a",
    "85fa7abff622aef16ed4",
    "848a7143c483f0eac4d2",
    "370f6d61c3ad953afc93",
    "2405d9bec5a9780dfd5a",
    "596d7d5632575cf8c0d3",
    "8a3e4c207762b72f4489",
    "443099499cbe2bb4585a",
    "5d533c44d5cba75d9a3f",
    "f6167a2127f43da50c81",
    "24dd640e42380bbbeba9",
    "e107e4bcdeb45bc221d5",
    "da2ee36274cccaa8d0bb",
    "112bb827838c6e856735",
    "0a84f0da8d38a403b720",
    "cdcfd501baaa41f24816",
    "64dd5fa7a2af3d56cc4a",
    "ca652c960c179878b653",
    "d0d9fef04fcd34c0fead",
    "9904ec2ba83f7760cd8a",
    "91050b1740c8318bdb10",
    "a9c6ce7b6e1ef2011142",
    "2fadbad51f12c1ab54f3",
    "f204a0f0dbee6a144dfa",
    "dfdce0489bc171db3cb3",
    "f92f0d8ba007aa9fbdc6",
    "f532c1b0c6b1697017d7",
    "0a7b3910ae20006172c8",
    "2613ab56e3a07f09faf4",
    "674719c22ab2e0ca70ac",
    "83af648dcbff5459169b",
    "afe3d23b46f59b859c3d",
    "577544484838e34d9b85",
    "fb1ad48884fde3279445",
    "74003743e226bc0953fe",
    "69e6e63e55c484ef5f13",
    "91136f281907c96e7948",
    "7d8f6cb4f39e7ace46a1",
    "299c4735fec1943c9d78",
    "4662f196b9403109d84c",
    "0f88d8e53e61e4d272e8",
    "72ea2edf1454c207b9e4",
    "96267169139e8e0482fa",
    "269a975592477419a682",
    "9de8d5d832e9f6b994ca",
    "a15bb62715746536a81c",
    "b3973dc2d0820f549554",
    "3024e4562fbd1c16ecaa",
    "abde3a3921b8204dc71c",
    "5e9e620cc7f37af2fdb1",
    "108c8acffefeb5915cac",
    "bdd5f8e8350386da8f66",
    "c5806cf2dde731761509",
    "3c15b4d686543fa25792",
    "de69a4128064ecad928b",
    "650d14e19b330a61ce00",
    "f97b4a3859e9deed32f0",
    "6614ce5fcc9ca84e4040",
    "0cbffd3e75385ba18dbf",
    "72b3226bb36896837d27",
    "d0ac8be05ee3eef2c2df",
    "08be8add318bb84a7352",
    "dfcd360a854a6bbc7d67",
    "95247beccb4eeedfd519",
    "67988f5a607ec02efe5a",
    "99f49e4714cee0874da6",
    "0db14a89b06d08e54816",
    "15c8532eb9eedeb708c4",
    "14243bc7c68dc7bfcd29",
    "b188aedde8ccf60ef0f1",
    "d5c0826a2b06f2e83b2c",
    "1b2dc24ab59f12d861be",
    "0832d184f6d8c04fc903",
    "ac916e691e7b40403a52",
    "ca4223a5158c644aaa61",
    "de42e5950dcf247beb7f",
    "f52bb6287f67ff20f21a",
    "8be4f630a30004809bfc",
    "8630e7c929db446e4aba",
    "a0770aa5a3761c866a72",
    "636c3616085c8d95dd03",
    "b9fdfcc05bc4f70ca868",
    "867fb1e42dc3f7df445b",
    "f7a4af15a3523c6cd044",
    "f7ebed50e24754f58f15",
    "ce6c307a4c4e7f6fd3f3",
    "4fc9ed0b7de52cd30a38",
    "122638066455f42da92e",
    "5a9ff2c680825f8a5255",
    "48a253136f19ddacc87e",
    "12585780ae0a76a3a852",
    "056a7d304c36da41e4d0",
    "b8e882c77f06f05c4f08",
    "4cee84ce6b6f11f6d127",
    "7d7791ea66bc990bae1f",
    "9e0f528c777b3a91f07c",
    "e75b49ba688079e3ec3c",
    "b5d43d7b0de7df7b9ad3",
    "ba78b355a8aa4b1be488",
    "3f0597a3091415d7101a",
    "6abeb3be9f664d2315c1",
    "38dd625baf5fbbaeaf44",
    "760129738669c768cace",
    "6ceb8bd41c920bee6b06",
    "86522fc063c022f51984",
    "efe4db4045747874e981",
    "cd5bf738ed7cc6c9ba0a",
    "0802e1daaadfa9521f1d",
    "d47729656db4669307cf",
    "7da574a6a3c885d4e6bb",
    "50f5e063d98f7d488009",
    "81dac85bec07d154df5b",
    "9a83a771d6d221c74b4c",
    "dbf9692547defbad37de",
    "586f2ab5d71394aeaf26",
    "a7522702c27c439c2b41",
    "c3838e6a7435d30f030d",
    "ce40a2bf32db70e6820d",
    "43c6f41dd9197bd6f62d",
    "de6dbe60b14200707a70",
    "b93fcc03428d9f1a8e80",
    "c5529bddea63eede68ac",
    "f8e1895516b508725303",
    "c1a8801007e1b017883b",
    "352250ddfb584653c26f",
    "eabe85f3e2be5aa8b006",
    "f3252061d0748d46ba92",
    "f2c3c146c314812a86c6",
    "da8b7e036d17f43d2908",
    "050137d27a0a1e9092cb",
    "aa63d288a1fd6c225be7",
    "d81c092685c7442ff698",
    "fdfac9429f621a24966b",
    "851711ab6b791dc468d4",
    "2a6a3a52a345a9d3c868",
    "2190d831b8ab0b310e03",
    "a5d445521976297f4a31",
    "0fc173cfe662667437d5",
    "834d53344e117b9b4eaa",
    "e522fc6001951c31b84e",
    "b5f639477acb435affa2",
    "bf0861e4d2c8bb7bd527",
    "932130f1a8ef167268c2",
    "459c4995aa90d9c61698",
    "82d47c94f824774411ad",
    "f062ec56d1fabd6c2321",
    "e835b353bb483150f255",
    "a843f6fbb283e6af95bb",
    "1ecbf86ebe2acabb4198",
    "c01b575c880934683daa",
    "8badf83f32be482d4b1b",
    "151b767fdacbfe6bee97",
    "35141d7869e0b12887a4",
    "ef1cad218db0a958200c",
    "902823f1c46435b5a9f8",
    "8fa3e7848b6c0cd10936",
    "282a57a37a985edd587b",
    "9c0ed9c22a9fe5770ea2",
    "4391da7786482b3c4179",
    "8fd3b1a84c71f78b41e9",
    "4989dd67d5c02a8cf4a5",
    "2667d4ff748a338b60d7",
    "b61d1355ea649e72e5de",
    "641dfe1ea3ca47823156",
    "60c0303b20868546bea5",
    "59122ef5151067cf0a52",
    "3b84a894e952b2c86b20",
    "1aeecc382299adbc687e",
    "b48a3c9a710b4fea07c6",
    "23f00eb4bc249b602f1b",
    "e647a632ba1eb21f32a2",
    "ec5404adc37825ec1af6",
    "74dc9755fd629d950ec9",
    "e3f26c8a9fc5dce72ca6",
    "c546269eab5f2137971c",
    "473f3d8fd44f03884e93",
    "f6a83e8862281391c187",
    "cee1da824711b7d63d90",
    "4a5174fa6e0d5d07f551",
    "58974b14fd49c6fe73e3",
    "65d994c4d267c3806eff",
    "8f021d96225ae34dbda6",
    "7c7c9d20288c236d0869",
    "7d0a3ac30fb00380c29b",
    "87a1a88f5a5b2d3b4f95",
    "2067a85a62bf9bb03856",
    "c07a17997614e559da0c",
    "525d008c1e3158388a9f",
    "29037c6e3adb5aec7046",
    "f404be7369b5152ae630",
    "a62ef37af5949beb0fac",
    "a73fc82a335d079e6d99",
    "40592ef1bd59d195b0bd",
    "72f07a2a4a2c80794079",
    "a8013d3ba2327a18f1f8",
    "86aec0c29b5fddd8d22f",
    "343a4469a3210ecdb817",
    "38b14606881f923b2fa9",
    "b9aa487d292512872186",
    "d0cfbf7687a7186acb9b",
    "8b1b7668372ca8f3afe0",
    "dedf117f63878e59f258",
    "7b50edc27d053687b4b3",
    "01968744a23b9ad6a40d",
    "f3c8dfaa09aed2c6c76d",
    "6ca95fb3c54174b9d013",
    "2ad45cdabece0993ae0f",
    "f8bc0846461ea01b340b",
    "d49f57f71fefcdd89466",
    "329d6c11ad9c40a2d1b2",
    "c2992262707086273b6a",
    "2aa0a7cb0dbed5fa3f69",
    "e2e36c66b318148ce4d6",
    "0cbdc7b16a7949cda74e",
    "8cfef0a05ada678b6de4",
    "33db600c024dc538b2f8",
    "57e9542702741e8d2bc6",
    "2c707adbb426f47c607e",
    "b69964f6349173fccf17",
    "7fc904fda348d70e658b",
    "2b361dcd58532faa0421",
    "06f1f021e22013d2a554",
    "571be36e29e3d1c055c5",
    "5dd0aeb4ebefc2b6eb43",
    "d3d06f35925fa2ed03f2",
    "bb69aca537cc6084d5cb",
    "dd80e896ebaf442b56d6",
    "c3cd899a03f3c0be8b64",
    "bd01a4430cb4b5ca3085",
    "c5612c91fb5a98d9f2ad",
    "51eef529f6e5cfc7055a",
    "c9b1460225d12d4cc85e",
    "240f7941fe056ecc8aa4",
    "0ff13e5d26329feb0145",
    "6ee54676b269ecd144cd",
    "bd8f0207961743c87653",
    "eedecbd10926994203b3",
    "5ec6bca3ac43ea5e9900",
    "3d23380f4ca9612fa152",
    "e2decec3cb7b0ce09955",
    "aa14b9e19a8d4b058136",
    "997e2f39c1ac8ad9c9f8",
    "b1bca1c1be8c9b3aa29f",
    "27e054ceb22b0833d302",
    "96663f3299c5f14f05ad",
    "f28d8c6f1c8af5e3e899",
    "a191195cd9da10fe96f0",
    "910621c14bf0b401f6b4",
    "e24274fefd6230cdda6f",
    "35093ecf59f62045624e",
    "5b582439796a6428e459",
    "7b64d7b31df9a0dad25b",
    "77f44a598882c661f65d",
    "7087ce37964ebf0969fc",
    "e10db5b363237eee9d43",
    "996f0eb56c4aeb7524a7",
    "cb1cc11cbd4c0e8fb8ad",
    "5a289b3fbd5c0cebfffc",
    "64c17415abb39ef40a39",
    "f444b8435fbbdfc9de71",
    "344dbe7ac48541806550",
    "f191082350d3acf426ad",
    "9fa1fc09256754215d99",
    "ccf2adc25349175cff22",
    "dadc608b276f642ada78",
    "89b6500a35a5d607197b",
    "6f9f617042e5dc6296fb",
    "1621f36c76a1921e674e",
    "361dee3609b0c280e9a1",
    "37b90c82c9ca711e0790",
    "0fbe5b2e3e5f06270b50",
    "d8684ff814cfc59142fd",
    "7427462165d7cf254007",
    "e20636ff7affcb637434",
    "18952a83af94d1d0f608",
    "91c8af56eb1e97eafb57",
    "83c02f67c5ba5cc3b684",
    "b83685c4a8f89a5d7f9e",
    "1f91b4b9188963c1dfe5",
    "d1dc95165b366d13aa13",
    "2063aa7503003427333e",
    "c4f5bf616a43f0f545a3",
    "7ef2fed33bd1f7cbee64",
    "ef2736cb235169302cbb",
    "7e18e939fdf9ecb78602",
    "ce74324ce165c480a57b",
    "1cfcc52401484d46ebea",
    "d21b81fddf95bfc734e1",
    "aa19ac6f7a0e95ae37f0",
    "d044e335eb4c4ac0776d",
    "7619bad26df1d25db5e2",
    "27654e5212d46d94aa61",
    "6320fbe34932791a66d0",
    "2d687df812d6cfa7c8c5",
    "04bce9e714e6ec22f98a",
    "1471c8ccb468ca4bf452",
    "1bbf4d54b45adbdadc63",
    "7849d932144bd716922d",
    "bbed38ba620c91bbb9a0",
    "bd4470c569fd2c842435",
    "71c1338f6b79f2090730",
    "fbfafae938b7a13f41c0",
    "c03d4160939d8aa5b68d",
    "aa451f8d5823ceff674c",
    "12fcfb3e2693096d94bf",
    "c358fd06c101cb32fca6",
    "af5d9d5d02ac8e42cf60",
    "3c86f3ac73ea99ab520e",
    "cb76d6e605d32ce964d9",
    "f9afbca8b675a68300ef",
    "57385db3bc842607e290",
    "3ba227a8d3b4e322809d",
    "3c6ce3b529d40e9630c4",
    "ad22a2ba167a5271eb82",
    "83f4dde9fe614a0fa076",
    "f4aa1960c52b43244911",
    "a25a43f9f9d435bae819",
    "9e44bb556f65ded2bbc4",
    "6dc145fe0ca08e31f8e8",
    "0090f404246c11a27265",
    "567aa96a6a0fedea9d63",
    "b92c2396565d23de37a6",
    "90917f8b9000d3e30d58",
    "3bcf974214b2792dddfe",
    "8b0098053a2eb95aff8c",
    "940ba5242a6582966e4d",
    "926876aef2f2bfa97dce",
    "58bbd63a27b40b230ff6",
    "14460c75bd324989b13b",
    "90e3bfdfacf8924a60da",
    "c2fc80b7892affec00e5",
    "a7fffcc4d318f9a29d83",
    "fd85b44214598f469d91",
    "e42af273007caca6be70",
    "79bdf8479d4add41b0bf",
    "673353b07b3d8e308f98",
    "d81013f0550355b11c6a",
    "953991fb043ae7363a19",
    "885d2f3a81e9d519868e",
    "f159fad1141e3ab0927e",
    "47060c8cb239110c6d16",
    "15dd9392cbec3fbcd881",
    "2871425bb666560d7935",
    "f1c284a5f57dea51121e",
    "caaa6a9273ec870a1e6b",
    "7de1f5652cb84f6f5365",
    "7b41626d6d900f49f0dc",
    "b34a1281dc709b05a352",
    "dda987850e75ecdac185",
    "77235fec3442cebf48d3",
    "2db0975f5cb5a34ed0cf",
    "7d233a6571d8f0f33b1a",
    "a0177c1c717729020541",
    "0e670b2c0847f110468c",
    "d62f8e26c6286dc69070",
    "c44b83dd83080e395851",
    "d6274ae4a51dd6ac8d2a",
    "07ad34f52031c72909e3",
    "99b71bee0c390c86b8d4",
    "44381b77cb805552b34b",
    "52e1182e91cf0563d3cb",
    "7af6cd88ee7b5fbeb71c",
    "063b5bb13e83b56c8135",
    "11573330f0e071143b18",
    "470b72b2d7550357477f",
    "fc96fe20a3dd0eec302e",
    "d1667a71218488b9736c",
    "8b0051293451b0d51ade",
    "b0f78e5753c9b78f1fb0",
    "67fdd7dc47697705155e",
    "f150d524e47bd5a03387",
    "4440b083c23859004b01",
    "02b1ac89a211a747f2c8",
    "2f9f42cd7501f98277cb",
    "723a3d33fc706cee73d7",
    "5ecc598f547455fab25f",
    "d5924c4d9da29f94cf57",
    "8a0deb748c9f1f1c4b8a",
    "5316a437e0410b730fc7",
    "f874f1cb4ff22976395d",
    "d29a1c5e566a447313f8",
    "3a633e16e4169bf51eec",
    "1b95cfb96e6ba82703d5",
    "1153ce96cfdbbbd3d148",
    "60e05befe1092911dae2",
    "1c5794dc2360b2663600",
    "c21dbb033798731de81e",
    "9e5a49a407b632eff021",
    "414067419fbc3e105e1c",
    "9fc8fde265cc2405b2fd",
    "952c350b2460407b2881",
    "cb61cb2983d809e084fb",
    "c41d04f73fff75399f85",
    "5481feaaf386aea0824c",
    "1fbd07f7f72b616706be",
    "84eb1759030ba44ac930",
    "3637f9de4557eba7b3da",
    "49fa9d3e64eb7e0ddafa",
    "31742920e909e312a37c",
    "aef383aaa7582f7891e9",
    "528ec928653d0e971220",
    "8f2e9dd4511c5ca06755",
    "583d5b2660e196d4c947",
    "42973f2fe06d3abc16e8",
    "0b3d905767071af00c8e",
    "2bfe7714532fe2ee7763",
    "c93d8ec4d873c84f3f47",
    "f6d0caa111a861a96543",
    "4769ec9bba30f00761e8",
    "3e44437ac50965d5e629",
    "588c50644c0fe34c293b",
    "54c3ee55fcb062d99eee",
    "51482e30e2598d7297dd",
    "177b13bd28059c0e3bfd",
    "7dfe59981defc1db7532",
    "01e6cc569054897b1bd0",
    "968cbd9c529912bb67f8",
    "bdb69a9b7f31e4f61a80",
    "7b5725cc15b60328001d",
    "8d320166804cf94eac43",
    "519dffc513729256a8ca",
    "d1a1bb715233c74a9c24",
    "fd85cd9314f0faa28ba1",
    "7600708a8d207ba61982",
    "fbacb6ae800f15e6758c",
    "b20df1ee1b2bc25ff48b",
    "273ec8f3c9b19dff8bda",
    "0bbc6bde1962279fa203",
    "b558aac2495ce018f020",
    "9862b92de7098eefa761",
    "02236175a64ced0932b5",
    "f2d9f848a9af0eb416e6",
    "e8dd518ae63e6f34fe11",
    "bfc6860554b440592d77",
    "eedcb4d08684814381d0",
    "095e1fd962c9699efa69",
    "608a7930f219fb35bf9d",
    "b520a15758844038428d",
    "d6097968cef94090e613",
    "9212f4b45172c04c6ad7",
    "93173577f20a84908fd8",
    "81924192f65736e90675",
    "653c891b2338e56be7cc",
    "4d3008995999801a3cbe",
    "0975a219372011203197",
    "f381d5893dea4599e072",
    "0c8eed232a34979fc8c4",
    "2d256300260aadf8f0a6",
    "c03640ca0a58fe267fa7",
    "91d449bd4c7fd69c9afa",
    "a96131b5beff3776a9dd",
    "07206bc8fcd6ec0054ef",
    "38c343395f6d7ad3a751",
    "9a5fa415de281c1794d3",
    "f510b3c4c9e1139e89ee",
    "2b313bb06d500f73c825",
    "78f2177e8e9415a4bcee",
    "2067a702afe18ee60738",
    "fb8a8300a30d495f372c",
    "5223e156324c9d8a4c0c",
    "27e5a963a08a47ae581f",
    "7d946ff3a1a6f2144720",
    "60345602c1970122b8cf",
    "37096e5e9992fc6b2d9a",
    "c321966b606a5689f12b",
    "cc070ba6b27f6e4227fc",
    "fdd87cb63be437bc131b",
    "fb429c716e3532f37d6a",
    "31f4bd8daa81a172fc4f",
    "0765d0013fd9cdf03abb",
    "b4af8c8628064acc02c6",
    "6074e6a3a197251144e5",
    "6d47dbab9bf0cfb640db",
    "e5f04f4baf3a0858712d",
    "2e894794cd3939588eed",
    "e1c989022c13b15152fb",
    "731b078e429410a8f9a9",
    "a5900f2899578b39706d",
    "1049c980ab5ac35c38e9",
    "570dba437ab0f969432c",
    "f15c15fbba54fcaf61e2",
    "67b385e5df17e98cdbe7",
    "81737a7600201842f2bf",
    "a937de3dbb738f3b904e",
    "02022fa51a6d8ec0c69a",
    "8eed93ba69d1be2527de",
    "1190cb7bac2a2432097b",
    "9028a6af2a849c7766f5",
    "ee41420586c25a668464",
    "290c2a165a2e68b91eaa",
    "ceb67111b8c2c0ac72fc",
    "6cff83821803c2671eb2",
    "9d32cb74cb2316152225",
    "d4654a5176c315447db6",
    "5b130a0fd9a65991dcfa",
    "846d18675cd72f85aa60",
    "b0eba8f5e107b5f930a4",
    "7e379bc3ed1fdfdd3df8",
    "5b06e520adcf26ae18e3",
    "fd72ab1750726ba92502",
    "54915d6d5e7160d6cd18",
    "11c7476857aa5d8a649c",
    "419acba5a93b264da281",
    "ab16d05f657520acc6aa",
    "3620674665b964656bf7",
    "06e612ce10c8295757bf",
    "2a9638fbe934d36b71e7",
    "292e7443236a72151d39",
    "c3a7322e46836f98c876",
    "0c584ad4b0fcc67092dc",
    "bf87f0cb7bc6d1561290",
    "3639b177b0ce525a19bb",
    "752387a4453d64ac5fe9",
    "63137d45025f10f141d2",
    "70783ed9d90453b11c43",
    "9c3fcc5dcc9d6d9aab80",
    "0fc1d6bd881e5675d8c8",
    "fea2884861813e3d36f2",
    "65c9595d958e1892d3ce",
    "153a440826c8ea5e34c5",
    "5738dbd540630373ab16",
    "cf7835a017121e18d2a8",
    "821c6e8a482d3e90371d",
    "520d780acb9e47e55a2b",
    "18fe40f065e9941fe70f",
    "2317dd6664fbea7fe5fa",
    "f2b59e8d6f321b7da55a",
    "5483ed32a44e47ad3d87",
    "d3e0827af7603bd54cf2",
    "f730b5c9b4b070eaf9da",
    "dd4c9d1450c7e9740f0a",
    "a53856ea234b680b034c",
    "b3c112892e57b925507a",
    "2d8be4386f1467844d25",
    "8f49bc96d2666490c3c0",
    "0aea09a95829638a1a7f",
    "7ba0951f3dbf83d4e95a",
    "0b34e4640e7123c339fb",
    "7f332582cacbf43fb001",
    "8f120f2305eb8f550d21",
    "f077732c07ef06c59179",
    "95dae8a92b543771bbd3",
    "6a003f8e985475f07661",
    "acea0d5d4452ef330e54",
    "1e80b583b9e9f0393cdb",
    "15c8a858a5017d4fa531",
    "c17c4b28f38f277ccb20",
    "235599ec06dd99267ab0",
    "60ca3fe4e2dce0eacc48",
    "e60ffae23971f0039f0c",
    "a648a2b700b68def3ba8",
    "0927f27627952054490d",
    "8fe8d14c502e3c66077e",
    "6b614083ead9f855259e",
    "adc554c59a8329778fef",
    "e66d8dc2f5cf89f58749",
    "1aaa5b10ef9202ebd6bd",
    "df4954ca18f0db98df14",
    "13e8aee46125be5b5018",
    "e113b22e8f451dd08f55",
    "2292928542538f868d24",
    "e823f446c8635799267e",
    "e3994a657d273d42d384",
    "d116d4a60c919b00bceb",
    "03a16cba4a92ea6a79e4",
    "04725a868b433d0aa1a1",
    "8ce2d77cab42de350af7",
    "5e9cec57c8a9823acc5b",
    "1f0c3d8afa75b9b7ae08",
    "5d04cea49389cee805c7",
    "b4dc3c18919a3b029ab0",
    "000451f9701a2e5869c7",
    "361974a6c3da827957e2",
    "3cca1de6c5c3661f617f",
    "143885e30355ef59872a",
    "fc34033200c77c7333d9",
    "232b58dbf6799868e224",
    "928fb799ad6ccdbcb202",
    "2c14ebde9f302e748930",
    "32e13597db3953c20918",
    "902af60c268a8dba2428",
    "e2dcdd16be9b8071594f",
    "3ddf495d9f1c041275a4",
    "f27490ebb3b9dea65496",
    "e18e80214a75c5ac15fd",
    "cc8656cc1bf1b99afe51",
    "e8365ffc194e8bd73d89",
    "53b2ec8ee9fa19dfd9bd",
    "ea2fe1cc713a13912365",
    "3110cc8c95585e02ee61",
    "ee1bad4e486f369c30b7",
    "d83eca157d6dfc79942e",
    "b1bdda29df1a72449cf5",
    "971817c650cb364bbaf7",
    "a5ba24eca7bbc2f3cb61",
    "cf1537ad4632f7175cfb",
    "93b8542daf55ee81a930",
    "c83e7d432b2e0f0a3b26",
    "c42fdef6e3efc3b7e131",
    "e55f8eca3ff36cff4755",
    "9092a05a77416736e567",
    "9bfb0618d2146ec86f80",
    "8a77294bd6228745e5ac",
    "2c91648cd7b9e28a2a3f",
    "5396a8f375b7f27c6cbd",
    "d771548a894dce66976d",
    "b743c24b8f7d07a082a5",
    "67a7147b639516b02a0d",
    "5fe661641077086a26e4",
    "eb1391e90ac464f94935",
    "445797cd51b3b616e2ef",
    "9d3607a4fc19afb70635",
    "709d707db40eab9584fe",
    "35634d879fcf2713a104",
    "a0734b76c386076b7c13",
    "de0e709f90a753843cd8",
    "c0a6d1c5fa8ed9e812b6",
    "95640fda684a7d6c987f",
    "9152604639e645601bcd",
    "7d9cf30ff80209892925",
    "bd7b3c7a5046dd07622f",
    "00548e93e6e7d924ad9b",
    "360a26b58616c58adbee",
    "ef42d5a118c2af4791ea",
    "334156555b4b6a53801d",
    "7aac8e160d08964ba5da",
    "68b7e3271dc4c977b740",
    "cf5cd1064efca39a76cf",
    "13cbe77498ae884c7b72",
    "e5a7e3a009bc44dcf8c5",
    "a591e6df5d8fc4d5adae",
    "35782ecaa2c08b606d83",
    "2c7c9c2c15908d07bf07",
    "6a3d3b1688013006c3c8",
    "21d30b6875f9343b601e",
    "97ac7609735e74e364ab",
    "e42caeca8be470bcc070",
    "ed17032d00bba117c044",
    "b47e2ce87b9ce2e36536",
    "d862dd776bd60963a2ff",
    "10473b1fb0b53fdd7208",
    "4e9e0438c8c5e6d1487c",
    "67ce7f06b974593414ab",
    "2d8438245c252627d86b",
    "c6293b82a01d25e87a14",
    "0d3844f35cff98332810",
    "5171024ac03a7661136c",
    "9f21393e96870ac00274",
    "0f811596bc4d34201c1b",
    "07f54385fc39c9a5a7ab",
    "474e6a4a5ac7a85af513",
    "7420debf786f4d5e5aa6",
    "ab99407a17b0d5ef9d35",
    "c36f15bdb61f1b695bfb",
    "3b8f65206f8a6827123d",
    "63096091b17ac3dc2df0",
    "33d50b9c9714af45810a",
    "220ff2f5ed248a01fd8a",
    "a11fca8a9f12181ee548",
    "85a6e3a8b340351c7a1f",
    "bc0ba255c2234f84c4e0",
    "0f7f3fff04e151d0a2e7",
    "a7cb5bf14799ee0e9d44",
    "caa33dc497012d7b5ae1",
    "cbb0ce5b59dc41afb664",
    "2a6b17d4f493d4c70688",
    "4fcc6dff92eab401a5b3",
    "d6c09f88b05f6ed5131b",
    "f9dd15c5e4856dbf8b8c",
    "0e9e6212d4bc95712197",
    "9207d8e1452385bf4cef",
    "a96b1ff26d21e80cb66b",
    "1e36687e80c962809b87",
    "7b3825ec298b1122c397",
    "97f47bb90325f67251ce",
    "30934747075823d4388a",
    "498c3632468303d65b7c",
    "e2a616c88ff47fbb215c",
    "e41ed284131ae279e36b",
    "977c23a6dfbcff317d33",
    "257c335083234c39940e",
    "1b6af65e01d9f8628fe9",
    "d3e2aeb9c4379d21c68a",
    "c68ce5eedd988d150d49",
    "e47d07fd13fd2700ed54",
    "2bdc81e1331b14764e82",
    "2efc0d89dc1caa8e960b",
    "7cb058f125c41264aff3",
    "b73be7d84f26b56a3c6d",
    "2ff9d055bce9a2ba7961",
    "809d819e8a62ad58d0a3",
    "3177d7e9415cec7fc134",
    "472a1bbf79c9ff03b998",
    "a59265f2303543c1375f",
    "36bb0e26c920d2eea3a3",
    "e6ca7043c61a244dcbaf",
    "6f76ae99637dc10d208a",
    "a879fc2fb5ae76fd7da0",
    "2aa2a20997a20ff0c48f",
    "81a64250da60bfe85af5",
    "dcc6076cdc90b65ff3e2",
    "8c4835bbb230463fe5e4",
    "5af93c974481f5ae216a",
    "398145641a0f06d82f3e",
    "95b230e6c7f7ee24cf22",
    "45079780a33a5b13cb01",
    "e1d9f95b5d01a3331cb3",
    "eac742190a4c127ccc53",
    "d8eda047f663e152a78a",
    "492fe4518c52656dbf65",
    "93bdf4b62353e66c2b87",
    "7c5a92018ff46776c144",
    "6e0ce175b75560b716ff",
    "4796063afdf72a02726b",
    "0ae113ebac707cfec487",
    "f2d0ac841fd56e010863",
    "540df02aea37bd5e4935",
    "117c48587dd86999e6fd",
    "acf8903df76c9fa4da9f",
    "9bcf8b28182c46fd15b3",
    "0c5ccd3753c192906541",
    "37faa5ab0d3b79b187ea",
    "dcfe4fd538efaebdf8ce",
    "ed34bf3b1be61cd6895c",
    "fd834e3143055c36421d",
    "5ca55c9af05afd29fd14",
    "63a93db21e963f3f4e87",
    "c66afc76484077fafd6b",
    "f500be1669caa4bd845e",
    "2cb34df45b2dfaf8a9dc",
    "14d2a3357c64b9deeda7",
    "ca9ea22846a46f41e324",
    "0ecadfab490ecc6d2d37",
    "4547f17a762969776392",
    "39fc0a982892fdcf49cd",
    "b6dcf2b514f14f134231",
    "baf42dd7c67d61d701cb",
    "67ad677b6e2eca206273",
    "4e588cfdee62c545ffdd",
    "379e5a64578b3b04e37b",
    "846950bd43765eeed3e7",
    "72687e0b146216a6bec7",
    "c0df8b39a3d108c02232",
    "da2ab565a4c0a50ef317",
    "13eff52f0eb18cea81d0",
    "a0ad2f3905a006ca5bd6",
    "e9a3d4fab1cd762812ee",
    "0d1bc47ff48f9721825d",
    "955a7a589021a2a5c76a",
    "cd26cfbc1b1254488093",
    "9a138c0743d943523454",
    "bfe08ba806bafe374612",
    "37942db0c1eae39b9d25",
    "d9d159a1d82dbbee7f77",
    "fa13ae30c38abfe14a70",
    "501ba0e495db885441ee",
    "0bae6fa6a1081e877186",
    "3acab9ffea734db64ae6",
    "1cc0bc835bcfa2a9fb20",
    "b12c88ce6a6c8e1a3144",
    "5a6c98723e97642d7b81",
    "e9c603a3bf09fb6af6e1",
    "6fe15844dbb935483c72",
    "701f26e1367bb29f37d9",
    "f79505646677564fa5ed",
    "5e6d6870e3d111dd361f",
    "ae13bb4daa2b8595f6d4",
    "0b579748bde0207d0e1a",
    "e2cb76ec8eb5418f0980",
    "1e120107aedebad7d1c4",
    "557ee5de14c055896997",
    "2c5e9ad27c84523ca854",
    "9e6cf8b3d95b11987952",
    "6d1cb114cbe0f773955a",
    "51b907926e3f6bc8b80d",
    "34b1b7e1657ce74b87ca",
    "c006fdb1f92996d52c7c",
    "b3a2e849210d622a6bff",
    "bf60318dc2284219a10d",
    "ce4673c5b4ab60c46ab8",
    "3149ee6e1e9b7fd3c1a2",
    "4815e54fa41a2efa4172",
    "462e9c28ea8591ae30be",
    "01f55e94c73b706ff910",
    "3c1bbe5fbbe851a6dd31",
    "200fc79c3fed1120a057",
    "d33cfc5b8474fd03526c",
    "68b7a34c450a2d4036c1",
    "cb5271a20ddb5ea84e78",
    "314b46cef8a246933cca",
    "ff2b963f95d5a6e51590",
    "10a207d8360292eacea5",
    "7334de3afcd4700f8159",
    "7df424b400a6712def44",
    "a62b948e54d232773f53",
    "2e13293c3ba37074addd",
    "6dc0025fed050dab4932",
    "817c98f0cee4b464959c",
    "a5b298a071091566dc48",
    "8da59f8c9bd417f8fc9a",
    "ca150ff45f14649a1b59",
    "8e69880b27f99525df36",
    "838d077fcf03f39b2b4a",
    "2a07ed58a95d9457e289",
    "487cb507a326a1310cd1",
    "216a0a4fc7366cc9f2fb",
    "ab3444d7702313c358b5",
    "56b5a3ed34a82788e59b",
    "c46f36bd166453726b7f",
    "5e824007f951dffbf2d9",
    "d2baa15a91273db3326d",
    "8c4620091f340c081b63",
    "61b2c49e5f3526a16cfa",
    "deecd93a24eb607e9a14",
    "ad1822a2f53ac4a8ee9a",
    "263cc9c1ad5344d214d1",
    "0323d79e6e05b7bdee21",
    "47a6845c31ff25bd0388",
    "48e8b521b4050fb3b74d",
    "8cdac80af53802c16ab9",
    "19b19d77f9bdc26415aa",
    "757a97783032c33f47c9",
    "583b55330f48bbc2aae4",
    "ad02d327a3c061685397",
    "e688a6a80c26a69e00d9",
    "c7fa8090dfc59fbdfd87",
    "1b5806802a33ba150df9",
    "9bd3694181072236ef23",
    "00d44622c8d64334ca37",
    "cd0434bb8eb0ab7bbb45",
    "c7da899f9b8d06c113e9",
    "b848777437f51b735c51",
    "bc3b99a1c9469bdbd636",
    "ac8b81756ac77336b44a",
    "3fe8eb057377b88b900c",
    "e79e72444c97006fcbed",
    "71f9878d138d8e2644f9",
    "4ccaed8196864a056094",
    "b83f46bc9b72d010eed7",
    "c6ccd09c7bd7f8f37b4f",
    "693d407bd2656fc063c1",
    "458d0973e8abd01d3147",
    "2c5e4e12b2aa1a163862",
    "9d05b32e72e225f90465",
    "2056e72a120402280180",
    "bc10de6bda5edec2d7f5",
    "2a34f09e99ab3a162ede",
    "701bee0fc5e01bd150f9",
    "7be3055a0e5c6d31bf0d",
    "2230a3d1499ca3b55af3",
    "e7ebfab789b89fc8a9e4",
    "c49bb7a14744f068328d",
    "a7147b95fcee81269556",
    "26ddd8f25b88b5dc71e5",
    "9e3952131adbb05571ca",
    "79c29eeba8ba6f1454be",
    "52e2d5cd8addc319e2d6",
    "06bd97025c3cc0ed67fc",
    "b36d41cddd204d6f9b07",
    "3b3f6cfb433aec5a70d6",
    "fe4c81b28c396bba5239",
    "b885990ff0d3a296f5c0",
    "201ab89a6d1b511bf4ee",
    "3879097ecd64a8a4fdb2",
    "5c4199c142429b2a96da",
    "529bfdffee36fb2bff16",
    "54a99708c65a25a86e19",
    "97c3af0f49c633a205e8",
    "22e4b8154b0725d9f420",
    "eb9aab74ce5046a89fa6",
    "1c9ad7d3384de9a9495f",
    "627da3b8c34451f1be70",
    "8802313ada5be535bd9a",
    "8bade5e511f49754c8b8",
    "7fdbd3c5ce2d1a594644",
    "8014c8b18f00ce8343c8",
    "189cf3743e4a31d9deda",
    "bd754ba15c0b23d65a1f",
    "07a18ac24d41b8ba79d0",
    "790cdbf0ba6d6276fe73",
    "368e6362d8b101197549",
    "02352b7d44b2829c9fee",
    "e5eeae5cfb262f777091",
    "e38a9a16a23387a2d073",
    "dd456280f12d47e9a969",
    "74fc05414e7b57e802c9",
    "37541a20749a89bae950",
    "26505cdac3bd9264f356",
    "a32acdf294df35ea23cd",
    "48a94a8e979b7513a5ec",
    "43a40af953e50ac4c8f8",
    "2ce25ef057838ebe8ffe",
    "de2228960da782f44231",
    "4d7fbb2e564d0124cd8d",
    "205c211130a0b5a54bb0",
    "cea2d2b1ca62e36a1cdd",
    "c8084e48a60a60d3f060",
    "5e6273a057da9ac7f623",
    "60c3493061b146c3bb1d",
    "a247a5299ae2e7b2a534",
    "2f29ac17df7020757c7a",
    "e71b27c059c277f08729",
    "7886f9e96af3add3d33e",
    "d8a9e85577eb6dacf557",
    "690468eb57426d46b59b",
    "88d6def604187c9bdea4",
    "3b4fac399dd51b4b6462",
    "108f1b1e74a570f9d103",
    "47d92bfb1f894f7c821d",
    "746d091e52e3f4f56edd",
    "655235c10145a9f2fd03",
    "743b1728344b92884758",
    "d9cc5a9ac70186f13b2b",
    "a92d59b49a036578d741",
    "b28decc6cb58c88dc460",
    "41a936cb60548639ffca",
    "6bef276be92dfea0be13",
    "aca7b0121355cc99e9d6",
    "f665bc48d1f070320c89",
    "f5823f8761bbb49e79b0",
    "34bccd99729457073837",
    "fa6d59cbcbfeb010da08",
    "9717f2d392367d8557a5",
    "258af6f0aaf5245ece42",
    "4231ba5e81fa606f7067",
    "b0920d0409ce26116e29",
    "cea88c5459766fad23e5",
    "6a5a47ac2c492a5fb5d4",
    "ac191c7910555baee982",
    "f878da5595509a7a7036",
    "4a67bd0d41ab5dbb076b",
    "f84cc60d652745059ca4",
    "1fccea261d659414d32d",
    "4b23534b224119493136",
    "c13510cf498d925a5c62",
    "c935b1ea73f69d4c8687",
    "7c0bf86a5fe3f59b358b",
    "f9bba9d8592a435fbaf4",
    "61bbf507f0c27a0014ed",
    "c899989f273e6aa59a58",
    "d74677fbde36706d3f62",
    "6c828dde9bd88242492c",
    "2734f5805b58fca7e084",
    "d4b07473d1ce6da118ba",
    "a4736351d5054b660131",
}
# Live pairs (Yahoo Finance)
PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
]
YH_HOSTS = [
    "https://query1.finance.yahoo.com",
    "https://query2.finance.yahoo.com",
]
YH_PATH = "/v8/finance/chart/%s=X?interval=5m&range=5d"
MIN_SAMPLES = 5
MIN_TRADES_FOR_FILTER = 10
MIN_WIN_RATE = 60.0
STATE_FILE = "state.json"

# ---- Settings ----
TIMEFRAME = 300            # candle / trade length in seconds (5 minutes)
LEAD_SECONDS = 20          # signal is sent this many seconds before the current candle ends
LOOKBACK_CANDLES = 10      # window used to find the previous high / low
COOLDOWN_CANDLES = 2       # minimum candles between two signals on the same pair
HISTORY_LIMIT = 60
STRATEGIES = {"break_retest": True, "breakout": True}
STRATEGY_NAMES = {"break_retest": "Break & Retest", "breakout": "Breakout"}
BREAKOUT_RANGE_MULT = 1.3  # breakout candle range >= 1.3 x average range of the previous candles
BREAKOUT_BODY_RATIO = 0.6  # breakout candle body >= 60% of its range
USE_PROVISIONAL_CANDLE = True   # analyse the still-forming candle so entry is right after it
TOL_SCALE = (TIMEFRAME / 60) ** 0.5
DEFAULT_CFG = {"tolerance_ratio": 0.0004, "min_body_ratio": 0.55}


def sec(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


def http_json(url, payload=None, headers=None, method=None, timeout=10):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode()
    return json.loads(raw) if raw else None


def sb_headers(cfg):
    return {"apikey": cfg["sb_key"], "Authorization": "Bearer " + cfg["sb_key"]}


def load_state(cfg):
    if cfg["sb_url"]:
        try:
            r = http_json(
                cfg["sb_url"] + "/rest/v1/kv?key=eq.state&select=value",
                headers=sb_headers(cfg),
            )
            if r:
                return r[0]["value"]
        except Exception:
            pass
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(cfg, data):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass
    if cfg["sb_url"]:
        try:
            h = sb_headers(cfg)
            h["Prefer"] = "resolution=merge-duplicates,return=minimal"
            http_json(
                cfg["sb_url"] + "/rest/v1/kv",
                payload={"key": "state", "value": data},
                headers=h,
                method="POST",
            )
        except Exception:
            pass


def persist(E):
    with E["lock"]:
        data = json.loads(json.dumps({
            "hist": list(E["hist"]),
            "stats": E["stats"],
            "rank": E["rank"],
            "reports": E["reports"],
            "n": E["n"],
            "used": E["used"],
        }))
    save_state(E["cfg"], data)



# =====================================================================
#  Forex data (Yahoo Finance)
# =====================================================================
def fx_chart(sym):
    err = None
    for h in YH_HOSTS:
        try:
            d = http_json(h + YH_PATH % sym)
            return d["chart"]["result"][0]
        except Exception as e:
            err = e
    raise err


def price(sym):
    return float(fx_chart(sym)["meta"]["regularMarketPrice"])


def get_candles(sym):
    r = fx_chart(sym)
    q = r["indicators"]["quote"][0]
    out = []
    for t, o, h, l, c in zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"]):
        if None in (o, h, l, c):
            continue
        out.append({"time": t // TIMEFRAME * TIMEFRAME, "open": float(o),
                    "high": float(h), "low": float(l), "close": float(c)})
    if len(out) < LOOKBACK_CANDLES + 5:
        raise Exception("not enough data")
    if out[-1]["time"] < int(time.time()) // TIMEFRAME * TIMEFRAME:
        raise Exception("market closed")
    return out[-HISTORY_LIMIT:]


# =====================================================================
#  Strategies
# =====================================================================
def is_strong_candle(c, min_body_ratio):
    rng = c["high"] - c["low"]
    return rng > 0 and abs(c["close"] - c["open"]) / rng >= min_body_ratio


def analyze_break_retest(candles, lookback=LOOKBACK_CANDLES, tolerance_ratio=0.0004, min_body_ratio=0.55):
    """Break of resistance/support, then a retest. The last candle is the confirmation candle."""
    if len(candles) < lookback + 3:
        return None
    curr = candles[-1]
    break_c = candles[-3]
    window = candles[-(lookback + 3):-3]
    resistance = max(c["high"] for c in window)
    support = min(c["low"] for c in window)
    tol = max(curr["close"], 1e-9) * tolerance_ratio
    if (
        break_c["close"] > resistance
        and resistance - tol * 2.5 <= curr["low"] <= resistance + tol
        and curr["close"] > resistance
        and curr["close"] > curr["open"]
        and is_strong_candle(curr, min_body_ratio)
    ):
        return "UP"
    if (
        break_c["close"] < support
        and support - tol <= curr["high"] <= support + tol * 2.5
        and curr["close"] < support
        and curr["close"] < curr["open"]
        and is_strong_candle(curr, min_body_ratio)
    ):
        return "DOWN"
    return None


def analyze_breakout(candles, lookback=LOOKBACK_CANDLES, min_body_ratio=BREAKOUT_BODY_RATIO,
                     range_mult=BREAKOUT_RANGE_MULT):
    """Strong wide candle closing beyond the high/low of the last N candles, close near its extreme."""
    if len(candles) < lookback + 1:
        return None
    curr = candles[-1]
    window = candles[-(lookback + 1):-1]
    resistance = max(c["high"] for c in window)
    support = min(c["low"] for c in window)
    avg_range = sum(c["high"] - c["low"] for c in window) / len(window)
    rng = curr["high"] - curr["low"]
    if rng <= 0 or avg_range <= 0 or rng < range_mult * avg_range:
        return None
    if not is_strong_candle(curr, min_body_ratio):
        return None
    if curr["close"] > resistance and curr["close"] > curr["open"] \
            and (curr["high"] - curr["close"]) / rng <= 0.25:
        return "UP"
    if curr["close"] < support and curr["close"] < curr["open"] \
            and (curr["close"] - curr["low"]) / rng <= 0.25:
        return "DOWN"
    return None


def find_signal(candles, cfg):
    series = candles if USE_PROVISIONAL_CANDLE else candles[:-1]
    if STRATEGIES.get("break_retest"):
        sig = analyze_break_retest(series, LOOKBACK_CANDLES, cfg["tolerance_ratio"], cfg["min_body_ratio"])
        if sig:
            return sig, "break_retest"
    if STRATEGIES.get("breakout"):
        sig = analyze_breakout(series)
        if sig:
            return sig, "breakout"
    return None, None


def fmt(sym, p):
    return ("%.3f" if "JPY" in sym else "%.5f") % p


def hm(ms):
    d = datetime.fromtimestamp(ms / 1000.0, timezone.utc)
    return d.strftime("%H:%M") + " UTC"


def analyze(sym):
    candles = get_candles(sym)
    cfg = dict(DEFAULT_CFG)
    cfg["tolerance_ratio"] *= TOL_SCALE
    dr, strat = find_signal(candles, cfg)
    why = STRATEGY_NAMES[strat] if strat else None
    return dr, why, candles[-1]["time"]


def safe_analyze(sym):
    try:
        dr, why, ts_used = analyze(sym)
        return sym, dr, why, None, ts_used
    except Exception as e:
        return sym, None, None, str(e), 0


# =====================================================================
#  Signal engine
# =====================================================================
def rel(E, sym, dr):
    s = E["rank"].get(sym + "|" + dr)
    if s is None or s[1] < MIN_SAMPLES:
        return None
    return s[0] * 100.0 / s[1]


def pick_best(E, results, expected):
    """Choose the best signal among the scan results. Returns (best, still_waiting)."""
    still = []
    best = None
    best_score = -1.0
    errs = []
    ok = False
    for sym, dr, why, err, ts_used in results:
        if err is not None:
            errs.append(err)
            continue
        ok = True
        if ts_used < expected:
            still.append(sym)          # candle not in the feed yet
            continue
        if dr is None:
            continue
        rl = rel(E, sym, dr)
        s = E["rank"].get(sym + "|" + dr)
        if s is not None and s[1] >= MIN_TRADES_FOR_FILTER and rl < MIN_WIN_RATE:
            with E["lock"]:            # pair/direction has a bad record: skip and let it recover slowly
                s[0] *= 0.9
                s[1] *= 0.9
            continue
        score = 50.0 if rl is None else rl
        if score > best_score:
            best_score = score
            best = {"sym": sym, "dir": dr, "why": why, "rl": rl}
    E["err"] = "" if ok else (errs[0][:80] if errs else "")
    return best, still


def open_signal(E, best, t, target):
    with E["lock"]:
        best["n"] = E["n"]
        E["n"] = E["n"] % 100 + 1
        best["at"] = t
        best["start"] = target * TIMEFRAME * 1000      # entry at the next candle open
        best["close"] = best["start"] + TIMEFRAME * 1000
        best["entry"] = None
        E["open"].append(best)
        E["act"] = best


def finish(E, act, cp):
    entry = act["entry"]
    d = cp - entry
    up = act["dir"] == "UP"
    key = act["sym"] + "|" + act["dir"]
    if d == 0:
        res = "DRAW"
    elif (d > 0) == up:
        res = "WIN"
    else:
        res = "LOSS"
    with E["lock"]:
        if res != "DRAW":
            if key not in E["stats"]:
                E["stats"][key] = [0, 0]
            E["stats"][key][1] += 1
            if key not in E["rank"]:
                E["rank"][key] = [0, 0]
            E["rank"][key][1] += 1
            if res == "WIN":
                E["stats"][key][0] += 1
                E["rank"][key][0] += 1
        E["hist"].append(res)
        h = list(E["hist"])
        E["reports"].insert(0, {
            "n": act["n"],
            "sym": act["sym"],
            "dir": act["dir"],
            "entry": fmt(act["sym"], entry),
            "close": fmt(act["sym"], cp),
            "res": res,
            "total": len(h),
            "w": h.count("WIN"),
            "l": h.count("LOSS"),
            "d": h.count("DRAW"),
            "time": hm(int(time.time() * 1000)),
        })
        del E["reports"][20:]
        if act in E["open"]:
            E["open"].remove(act)
        if E["act"] is act:
            E["act"] = None
    persist(E)


def run(E):
    pool = ThreadPoolExecutor(max_workers=len(PAIRS))
    last_target = -1
    last_sig = {}
    while True:
        try:
            t = int(time.time() * 1000)

            # Settle open trades (entry at the candle open, result at the candle close).
            with E["lock"]:
                open_now = list(E["open"])
            for a in open_now:
                if t > a["close"] + 30000:
                    with E["lock"]:
                        if a in E["open"]:
                            E["open"].remove(a)
                        if E["act"] is a:
                            E["act"] = None
                    continue
                if a["entry"] is None and t >= a["start"]:
                    a["entry"] = price(a["sym"])
                if a["entry"] is not None and t >= a["close"]:
                    finish(E, a, price(a["sym"]))

            # Scan LEAD_SECONDS before the current candle ends, once per candle.
            now = time.time()
            period = int(now) // TIMEFRAME
            target = period + 1
            if now % TIMEFRAME >= TIMEFRAME - LEAD_SECONDS and target != last_target:
                last_target = target
                syms = [p for p in PAIRS if target - last_sig.get(p, -999) >= COOLDOWN_CANDLES]
                results = list(pool.map(safe_analyze, syms))
                best, _ = pick_best(E, results, period * TIMEFRAME)
                if best is not None:
                    last_sig[best["sym"]] = target
                    open_signal(E, best, t, target)
        except Exception as e:
            E["err"] = str(e)[:80]
        time.sleep(1)


@st.cache_resource
def engine():
    cfg = {"sb_url": str(sec("SUPABASE_URL", "")).rstrip("/"), "sb_key": str(sec("SUPABASE_KEY", ""))}
    saved = load_state(cfg)
    E = {
        "lock": threading.RLock(),
        "cfg": cfg,
        "hist": deque(saved.get("hist", []), maxlen=30),
        "stats": saved.get("stats", {}),
        "rank": saved.get("rank", saved.get("stats", {})),
        "reports": saved.get("reports", []),
        "n": saved.get("n", 1),
        "used": saved.get("used", {}),
        "act": None,
        "open": [],
        "err": "",
    }
    threading.Thread(target=run, args=(E,), daemon=True).start()
    return E


def same(a, b):
    return secrets.compare_digest(a.encode(), b.encode())


def code_hash(code):
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()[:20]


def claim(code, email):
    hc = code_hash(code)
    if hc not in CODE_HASHES:
        return False
    E = engine()
    em = email.strip().lower()
    with E["lock"]:
        owner = E["used"].get(hc)
        if owner is not None:
            return owner == em
        E["used"][hc] = em
    persist(E)
    return True


def send_code(user_email, code):
    msg = EmailMessage()
    msg["From"] = sec("SMTP_USER", OWNER_EMAIL)
    msg["To"] = OWNER_EMAIL
    msg["Subject"] = "Login code for " + user_email
    msg.set_content(
        "User: " + user_email + "\nCode: " + code + "\nValid for 10 minutes."
    )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as srv:
        srv.login(sec("SMTP_USER", OWNER_EMAIL), sec("SMTP_PASS"))
        srv.send_message(msg)


def notify_owner(user_email):
    data = json.dumps({
        "email": user_email,
        "message": "طلب دخول جديد للتطبيق: " + user_email,
        "_subject": "طلب دخول: " + user_email,
        "_captcha": "false",
    }).encode()
    req = urllib.request.Request(
        "https://formsubmit.co/ajax/" + OWNER_EMAIL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    urllib.request.urlopen(req, timeout=15).read()


def gate():
    ss = st.session_state
    if ss.get("auth"):
        return True
    st.title("إشارات الفوركس")
    st.write("للدخول: اكتب إيميلك واطلب الرمز، أو ادفع " + str(PRICE) + "$.")
    pay = sec("PAY_URL", PAY_URL)
    if pay.startswith("http"):
        st.link_button("ادفع " + str(PRICE) + "$", pay)
    elif st.button("ادفع " + str(PRICE) + "$"):
        st.info("رابط الدفع مو جاهز بعد، تواصل مع " + OWNER_EMAIL)
    email = st.text_input("الإيميل")
    if st.button("اطلب رمز الدخول"):
        if "@" not in email or "." not in email:
            st.error("إيميل غير صحيح")
        elif time.time() - ss.get("sent_at", 0) < 60:
            st.error("استنى دقيقة وجرّب مرة ثانية")
        else:
            try:
                if sec("SMTP_PASS"):
                    code = str(secrets.randbelow(900000) + 100000)
                    send_code(email.strip(), code)
                    ss["code"] = code
                    ss["exp"] = time.time() + 600
                else:
                    notify_owner(email.strip())
                ss["sent_at"] = time.time()
                st.success("وصل طلبك لصاحب التطبيق، رح يعطيك الرمز.")
            except Exception:
                st.error("ما قدرنا نبعت الطلب، جرّب لاحقاً")
    entered = st.text_input("رمز الدخول")
    if st.button("دخول"):
        if "@" not in email or "." not in email:
            st.error("اكتب إيميلك أول")
        elif ss.get("tries", 0) >= 5:
            st.error("محاولات كثيرة، جرّب لاحقاً")
        elif entered.strip() and (
            claim(entered, email)
            or (ss.get("code") and time.time() < ss.get("exp", 0)
                and same(entered.strip(), ss["code"]))
        ):
            ss["auth"] = True
            st.rerun()
        else:
            ss["tries"] = ss.get("tries", 0) + 1
            st.error("رمز غلط")
    return False


def card(lines, cls="msg", stamp=""):
    out = '<div class="' + cls + '">' + "<br>".join(lines)
    if stamp:
        out += '<span class="t">' + stamp + "</span>"
    return out + "</div>"


@st.fragment(run_every=2)
def live():
    E = engine()
    with E["lock"]:
        act = dict(E["act"]) if E["act"] else None
        reports = list(E["reports"])
        stats = {k: list(v) for k, v in E["stats"].items()}
        err = E["err"]
    w = sum(v[0] for v in stats.values())
    tot = sum(v[1] for v in stats.values())
    if tot:
        out = ('<div class="sum">Real win rate<b>%.1f%%</b><span>%d WIN / %d LOSS (%d trades)</span></div>'
               % (w * 100.0 / tot, w, tot - w, tot))
    else:
        out = '<div class="sum">Real win rate<b>--</b><span>0 trades</span></div>'
    if act:
        rtxt = ("NEW (not enough results yet)" if act["rl"] is None
                else "%.1f%% past win rate" % act["rl"])
        entry = fmt(act["sym"], act["entry"]) if act["entry"] is not None else "at candle open"
        out += card([
            "SIGNAL #%d" % act["n"],
            "Candle: " + hm(act["start"]),
            "Duration: %d min" % (TIMEFRAME // 60),
            act["sym"] + " " + act["dir"],
            "Entry: " + entry,
            "Reason: " + html.escape(act["why"]).replace("\n", "<br>"),
            "Reliability: " + rtxt,
            "Not financial advice",
        ], "msg sig", hm(act["at"]))
        if st.session_state.get("seen") != (act["start"], act["sym"]):
            st.session_state["seen"] = (act["start"], act["sym"])
            st.toast(act["sym"] + " " + act["dir"] + " - " + hm(act["start"]))
    elif err:
        out += card(["Waiting for market data..."], "msg wait")
    else:
        out += card(["جاري البحث عن إشارة..."], "msg wait")
    for r in reports:
        out += card([
            "REPORT #%d" % r["n"],
            r["sym"] + " " + r["dir"],
            "Entry: " + r["entry"],
            "Close: " + r["close"],
            'Result: <span class="res ' + r["res"] + '">' + r["res"] + "</span>",
            "Last %d: %d WIN / %d LOSS / %d DRAW" % (r["total"], r["w"], r["l"], r["d"]),
        ], "msg", r["time"])
    out += '<div class="msg wait">Not financial advice. Trading involves risk of loss.</div>'
    st.markdown(out, unsafe_allow_html=True)


engine()

if gate():
    live()
