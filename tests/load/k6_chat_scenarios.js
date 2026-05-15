import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const chatLatency = new Trend("chat_latency");

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const API_KEY = __ENV.API_KEY || "sk-demo-key";

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

const scenarios = {
  ramp_up: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "1m", target: 50 },
      { duration: "3m", target: 100 },
      { duration: "5m", target: 100 },
      { duration: "2m", target: 0 },
    ],
  },
  spike: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "30s", target: 200 },
      { duration: "2m", target: 200 },
      { duration: "30s", target: 0 },
    ],
  },
  soak: {
    executor: "constant-vus",
    vus: 50,
    duration: "30m",
  },
};

const CHAT_MESSAGES = [
  "如何申请退货退款？",
  "查询订单20260507001",
  "我的快递到哪里了？",
  "会员积分怎么查看？",
  "你们客服电话是多少？",
  "优惠券在哪里领？",
  "我要投诉产品质量问题",
  "换货流程是怎样的？",
  "发货一般要多久？",
  "查询我的会员等级",
];

export const options = {
  scenarios: {
    chat_sync: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 20 },
        { duration: "3m", target: 50 },
        { duration: "5m", target: 50 },
        { duration: "2m", target: 0 },
      ],
      exec: "chatSync",
    },
    health_check: {
      executor: "constant-vus",
      vus: 5,
      duration: "30s",
      exec: "healthCheck",
    },
  },
  thresholds: {
    errors: ["rate<0.01"],
    chat_latency: ["p(95)<5000"],
    http_req_duration: ["p(99)<10000"],
  },
};

export function chatSync() {
  const message = CHAT_MESSAGES[Math.floor(Math.random() * CHAT_MESSAGES.length)];
  const payload = JSON.stringify({
    message: message,
    user_id: `load-test-user-${__VU}-${__ITER}`,
  });

  const resp = http.post(`${BASE_URL}/chat/send-sync`, payload, {
    headers: headers,
    timeout: 60,
  });

  const ok = check(resp, {
    "status 200": (r) => r.status === 200,
    "has response": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.response !== undefined;
      } catch {
        return false;
      }
    },
    "has trace_id": (r) => {
      try {
        return JSON.parse(r.body).trace_id !== undefined;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!ok);
  chatLatency.add(resp.timings.duration);

  sleep(1);
}

export function healthCheck() {
  const resp = http.get(`${BASE_URL}/admin/health`);
  check(resp, { "health ok": (r) => r.status === 200 && JSON.parse(r.body).status === "ok" });
  sleep(5);
}

export default chatSync;
