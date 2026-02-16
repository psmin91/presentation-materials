# 프리미티브 조합 실습

> FastMCP 3.x의 3가지 프리미티브(Component, Provider, Transform)를
> 어떻게 조합하면 어떤 패턴이 만들어지는지 직접 실행해볼 수 있는 예제입니다.

## 실행 방법

```bash
pip install "fastmcp>=3.0.0"
python 01_proxy.py
```

## 파일 목록

| 파일 | 조합 | 만들어지는 패턴 | 공항 비유 |
|------|------|----------------|-----------|
| `01_proxy.py` | ProxyProvider | 프록시 | ✈️ 경유편 |
| `02_gateway.py` | ProxyProvider N개 + Visibility | 게이트웨이 | 🛂 출입국심사 |
| `03_aggregator.py` | FastMCPProvider N개 + Namespace | 애그리게이터 | 🔍 스카이스캐너 |
| `04_router.py` | Namespace 접두사 | 라우터 | 🚪 탑승구 구역제 |
| `05_dynamic.py` | enable/disable + 라이브 | 동적 등록 | 🎫 등급별 라운지 |
