# US Stock Wealth Builder - 미국 주식 자산 증식 시스템

> **목표: 장기적 자산 증식 + 원금 보존**
> 한국투자증권 KIS API + Claude AI 기반 체계적 투자 시스템

---

## Part 1: 투자 철학 및 원칙

### 1.1 핵심 투자 철학

#### 절대 원칙 (위반 시 거래 중단)
```
1. 원금 보존이 수익보다 우선
2. 이해하지 못하는 것에 투자하지 않음
3. 감정이 아닌 데이터로 판단
4. 분산 투자로 리스크 분산
5. 손실은 작게, 이익은 크게 (비대칭 수익 구조)
```

#### 투자 대가들의 원칙 통합
| 대가 | 핵심 원칙 | 시스템 적용 |
|------|----------|------------|
| **워렌 버핏** | 내재가치 대비 할인 매수, 장기 보유 | Fair Value 계산, Margin of Safety 20% |
| **레이 달리오** | 올웨더 포트폴리오, 상관관계 분산 | 자산군 분산, 상관계수 < 0.5 |
| **피터 린치** | 아는 것에 투자, 10배주 발굴 | 섹터 전문성, 성장주 스크리닝 |
| **하워드 막스** | 사이클 인식, 2차적 사고 | 시장 사이클 분석, 역발상 시그널 |
| **조엘 그린블랫** | 마법공식 (저PER + 고ROC) | 퀀트 스크리닝 적용 |

### 1.2 투자 목표 설정

```python
INVESTMENT_GOALS = {
    "primary": {
        "target_cagr": 0.15,          # 연 15% 목표 수익률
        "max_drawdown": -0.15,        # 최대 낙폭 15% 제한
        "sharpe_ratio_min": 1.0,      # 최소 샤프 비율
    },
    "risk_tolerance": {
        "conservative": 0.3,           # 30%는 안전자산
        "moderate": 0.5,               # 50%는 우량주
        "aggressive": 0.2,             # 20%는 성장주
    },
    "time_horizon": "5_years_plus",    # 5년 이상 장기 투자
}
```

### 1.3 손실 방지 메커니즘 (5단계 방어선)

```
┌─────────────────────────────────────────────────────────────────┐
│                    5단계 손실 방지 시스템                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1단계] 진입 전 검증                                           │
│  └─ 최소 3개 이상 분석 축에서 긍정적 신호 필요                  │
│  └─ AI 확신도 7/10 이상만 진입                                  │
│                                                                 │
│  [2단계] 포지션 사이징                                          │
│  └─ 단일 종목 최대 5% (고확신 시 최대 8%)                       │
│  └─ 켈리 기준의 1/2만 사용 (Half-Kelly)                         │
│                                                                 │
│  [3단계] 자동 손절                                              │
│  └─ 개별 종목: -7% 손절                                         │
│  └─ 포트폴리오: 일일 -2% 시 신규 매수 중단                      │
│  └─ 포트폴리오: 주간 -5% 시 포지션 50% 축소                     │
│                                                                 │
│  [4단계] 시장 위험 감지                                         │
│  └─ VIX > 30: 현금 비중 50% 이상 유지                           │
│  └─ 200일선 하회: 공격적 매수 중단                              │
│                                                                 │
│  [5단계] 블랙스완 대응                                          │
│  └─ 일일 -3% 이상 낙폭: 전 포지션 동결                          │
│  └─ 수동 검토 후에만 거래 재개                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 2: 시스템 아키텍처

### 2.1 전체 시스템 구조

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     US Stock Wealth Builder v2.0                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      DATA LAYER (데이터 계층)                     │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  [실시간]        [일간]           [이벤트]        [대안 데이터]   │   │
│  │  - 시세          - OHLCV          - 실적발표      - 뉴스 센티멘트 │   │
│  │  - 호가          - 재무제표       - FOMC          - SNS 언급량   │   │
│  │  - 체결          - 기술지표       - CPI 발표      - 내부자거래   │   │
│  │  - 잔고          - 섹터동향       - 배당락일      - 기관 보유    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   ANALYSIS LAYER (분석 계층)                      │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  [기술적 분석]   [기본적 분석]   [심리 분석]    [거시 분석]       │   │
│  │  - 추세          - 밸류에이션    - 뉴스 감성    - 경기 사이클    │   │
│  │  - 모멘텀        - 퀄리티        - 공포/탐욕    - 금리 환경      │   │
│  │  - 변동성        - 성장성        - 포지셔닝     - 유동성         │   │
│  │  - 패턴          - 배당          - 플로우       - 섹터 순환      │   │
│  │        ↓               ↓              ↓              ↓            │   │
│  │  ┌─────────────────────────────────────────────────────────┐     │   │
│  │  │              SCORING ENGINE (점수화 엔진)                │     │   │
│  │  │   각 분석 축별 -100 ~ +100 점수 → 가중 평균 종합 점수   │     │   │
│  │  └─────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     AI LAYER (AI 판단 계층)                       │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │   │
│  │  │   Claude    │  │  Reflection │  │   Decision Validator    │   │   │
│  │  │   Sonnet    │→ │   Engine    │→ │   (결정 검증기)         │   │   │
│  │  │  (주 분석)  │  │  (자가 반성)│  │   - 논리 검증           │   │   │
│  │  └─────────────┘  └─────────────┘  │   - 리스크 체크         │   │   │
│  │                                     │   - 과거 성과 비교      │   │   │
│  │                                     └─────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   RISK LAYER (리스크 관리 계층)                   │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  [포지션 사이징]    [상관관계 관리]    [드로다운 관리]            │   │
│  │  - Kelly Criterion  - 자산간 상관     - 일일 한도               │   │
│  │  - Volatility 조절  - 섹터 집중도     - 주간 한도               │   │
│  │  - Max Position     - 팩터 노출       - 월간 한도               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                 EXECUTION LAYER (실행 계층)                       │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  [주문 최적화]      [체결 관리]        [사후 검증]                │   │
│  │  - 분할 매수/매도   - 슬리피지 관리    - 체결 품질 분석          │   │
│  │  - 지정가/시장가    - 미체결 처리      - 비용 분석               │   │
│  │  - 타이밍 최적화    - 부분 체결        - 성과 귀인               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  MONITORING LAYER (모니터링 계층)                 │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  [실시간 대시보드]  [알림 시스템]      [성과 리포트]              │   │
│  │  - 포트폴리오 현황  - Slack/Telegram   - 일간/주간/월간          │   │
│  │  - 리스크 지표      - 긴급 알림        - 벤치마크 비교           │   │
│  │  - AI 판단 로그     - 리밸런싱 알림    - 귀인 분석               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 모듈 상세 구조

```
us_stock_wealth_builder/
│
├── config/
│   ├── settings.py              # 전역 설정
│   ├── risk_params.py           # 리스크 파라미터
│   ├── watchlist.py             # 관심 종목
│   └── trading_rules.py         # 매매 규칙
│
├── data/
│   ├── sources/
│   │   ├── kis_client.py        # 한국투자증권 API
│   │   ├── yfinance_client.py   # Yahoo Finance
│   │   ├── fred_client.py       # 경제 지표
│   │   ├── finnhub_client.py    # 뉴스/센티멘트
│   │   └── sec_client.py        # SEC 공시
│   ├── collectors/
│   │   ├── price_collector.py   # 시세 수집
│   │   ├── fundamental_collector.py
│   │   ├── news_collector.py
│   │   └── macro_collector.py
│   ├── processors/
│   │   ├── data_cleaner.py      # 데이터 정제
│   │   ├── feature_engineer.py  # 피처 엔지니어링
│   │   └── data_validator.py    # 데이터 검증
│   └── storage/
│       ├── cache_manager.py     # 캐시 관리
│       └── db_manager.py        # DB 관리
│
├── analysis/
│   ├── technical/
│   │   ├── indicators.py        # 기술적 지표
│   │   ├── patterns.py          # 패턴 인식
│   │   ├── support_resistance.py
│   │   └── trend_analyzer.py
│   ├── fundamental/
│   │   ├── valuation.py         # 밸류에이션
│   │   ├── quality.py           # 퀄리티 분석
│   │   ├── growth.py            # 성장성 분석
│   │   └── dividend.py          # 배당 분석
│   ├── sentiment/
│   │   ├── news_sentiment.py    # 뉴스 감성
│   │   ├── social_sentiment.py  # SNS 감성
│   │   └── flow_analyzer.py     # 자금 흐름
│   ├── macro/
│   │   ├── cycle_analyzer.py    # 경기 사이클
│   │   ├── rate_analyzer.py     # 금리 분석
│   │   └── sector_rotation.py   # 섹터 순환
│   └── scoring/
│       ├── stock_scorer.py      # 종목 점수화
│       ├── portfolio_scorer.py  # 포트폴리오 점수
│       └── opportunity_ranker.py # 기회 순위
│
├── ai/
│   ├── prompts/
│   │   ├── system_prompts.py    # 시스템 프롬프트
│   │   ├── stock_analysis.py    # 종목 분석 프롬프트
│   │   └── portfolio_review.py  # 포트폴리오 리뷰
│   ├── analyzers/
│   │   ├── stock_analyzer.py    # 개별 종목 분석
│   │   ├── portfolio_analyzer.py # 포트폴리오 분석
│   │   └── market_analyzer.py   # 시장 분석
│   ├── validators/
│   │   ├── decision_validator.py # 결정 검증
│   │   └── logic_checker.py     # 논리 검증
│   └── reflection/
│       ├── performance_review.py # 성과 반성
│       └── mistake_analyzer.py  # 실수 분석
│
├── risk/
│   ├── position_sizing.py       # 포지션 사이징
│   ├── correlation_manager.py   # 상관관계 관리
│   ├── drawdown_manager.py      # 드로다운 관리
│   ├── exposure_manager.py      # 노출도 관리
│   └── circuit_breaker.py       # 서킷 브레이커
│
├── execution/
│   ├── order_manager.py         # 주문 관리
│   ├── execution_optimizer.py   # 체결 최적화
│   ├── trade_executor.py        # 매매 실행
│   └── order_validator.py       # 주문 검증
│
├── portfolio/
│   ├── portfolio_manager.py     # 포트폴리오 관리
│   ├── rebalancer.py            # 리밸런싱
│   ├── tax_optimizer.py         # 세금 최적화
│   └── performance_tracker.py   # 성과 추적
│
├── backtest/
│   ├── backtester.py            # 백테스팅 엔진
│   ├── walk_forward.py          # 워크포워드 분석
│   ├── monte_carlo.py           # 몬테카를로 시뮬레이션
│   └── stress_test.py           # 스트레스 테스트
│
├── monitoring/
│   ├── dashboard/
│   │   └── app.py               # Streamlit 대시보드
│   ├── alerts/
│   │   ├── alert_manager.py     # 알림 관리
│   │   ├── slack_notifier.py
│   │   └── telegram_notifier.py
│   └── reports/
│       ├── daily_report.py      # 일간 리포트
│       ├── weekly_report.py     # 주간 리포트
│       └── monthly_report.py    # 월간 리포트
│
├── utils/
│   ├── logger.py                # 로깅
│   ├── time_utils.py            # 시간 유틸
│   ├── math_utils.py            # 수학 유틸
│   └── constants.py             # 상수
│
├── scheduler/
│   └── trading_scheduler.py     # 스케줄러
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── main.py                      # 메인 실행
├── requirements.txt
└── README.md
```

---

## Part 3: 데이터 수집 상세

### 3.1 데이터 소스 매트릭스

| 데이터 유형 | 소스 | 갱신 주기 | 비용 | 우선순위 |
|------------|------|----------|------|---------|
| **실시간 시세** | KIS API | 실시간 | 무료 | 필수 |
| **과거 시세 (일봉)** | yfinance | 일간 | 무료 | 필수 |
| **과거 시세 (분봉)** | KIS API | 실시간 | 무료 | 필수 |
| **재무제표** | yfinance | 분기 | 무료 | 필수 |
| **재무제표 (상세)** | Financial Modeling Prep | 분기 | $19/월 | 권장 |
| **애널리스트 평가** | Finnhub | 일간 | 무료 | 필수 |
| **뉴스 헤드라인** | Finnhub | 실시간 | 무료 | 필수 |
| **뉴스 (상세)** | NewsAPI | 실시간 | $449/월 | 선택 |
| **경제 지표** | FRED | 일간 | 무료 | 필수 |
| **내부자 거래** | SEC EDGAR | 일간 | 무료 | 권장 |
| **기관 보유** | SEC 13F | 분기 | 무료 | 권장 |
| **옵션 데이터** | CBOE | 일간 | 유료 | 선택 |
| **공매도 데이터** | FINRA | 일간 | 무료 | 권장 |

### 3.2 기술적 분석 지표 상세

```python
TECHNICAL_INDICATORS = {
    # =========================================================================
    # 추세 지표 (Trend Indicators)
    # =========================================================================
    "trend": {
        "SMA": {
            "periods": [10, 20, 50, 100, 200],
            "usage": "추세 방향 및 지지/저항",
            "signals": {
                "golden_cross": "SMA50 > SMA200 돌파 → 강세",
                "death_cross": "SMA50 < SMA200 돌파 → 약세",
                "price_above_200": "장기 상승 추세",
            }
        },
        "EMA": {
            "periods": [9, 12, 21, 26, 50],
            "usage": "단기 추세 및 MACD 계산",
        },
        "ADX": {
            "period": 14,
            "usage": "추세 강도 측정",
            "signals": {
                "adx > 25": "강한 추세",
                "adx < 20": "횡보/무추세",
                "adx > 40": "매우 강한 추세 (과열 주의)",
            }
        },
        "Ichimoku": {
            "params": {"tenkan": 9, "kijun": 26, "senkou_b": 52},
            "usage": "복합 추세/지지/저항",
            "signals": {
                "price_above_cloud": "강세",
                "price_below_cloud": "약세",
                "tenkan_kijun_cross": "단기 모멘텀 변화",
            }
        },
        "SuperTrend": {
            "params": {"period": 10, "multiplier": 3},
            "usage": "추세 추종 및 손절 기준",
        },
    },

    # =========================================================================
    # 모멘텀 지표 (Momentum Indicators)
    # =========================================================================
    "momentum": {
        "RSI": {
            "period": 14,
            "usage": "과매수/과매도 판단",
            "signals": {
                "rsi > 70": "과매수 (매도 고려)",
                "rsi < 30": "과매도 (매수 고려)",
                "rsi_divergence": "추세 반전 가능성",
            },
            "advanced": {
                "rsi_range_shift": "50 기준 영역 이동으로 추세 확인",
                "hidden_divergence": "추세 지속 신호",
            }
        },
        "MACD": {
            "params": {"fast": 12, "slow": 26, "signal": 9},
            "usage": "추세 모멘텀 및 전환점",
            "signals": {
                "macd_cross_signal": "모멘텀 변화",
                "histogram_divergence": "추세 약화",
                "zero_line_cross": "추세 전환",
            }
        },
        "Stochastic": {
            "params": {"k": 14, "d": 3, "smooth": 3},
            "usage": "단기 반전점",
            "signals": {
                "k > 80": "과매수",
                "k < 20": "과매도",
                "k_d_cross": "반전 신호",
            }
        },
        "Williams_R": {
            "period": 14,
            "usage": "과매수/과매도 보조 확인",
        },
        "CCI": {
            "period": 20,
            "usage": "가격 이상치 탐지",
            "signals": {
                "cci > 100": "강한 상승 모멘텀",
                "cci < -100": "강한 하락 모멘텀",
            }
        },
        "ROC": {
            "period": 12,
            "usage": "가격 변화율",
        },
    },

    # =========================================================================
    # 변동성 지표 (Volatility Indicators)
    # =========================================================================
    "volatility": {
        "Bollinger_Bands": {
            "params": {"period": 20, "std": 2},
            "usage": "변동성 및 가격 밴드",
            "signals": {
                "price_touch_upper": "과매수 또는 강한 모멘텀",
                "price_touch_lower": "과매도 또는 약한 모멘텀",
                "squeeze": "변동성 축소 → 큰 움직임 예고",
                "bandwidth_expansion": "변동성 확대",
            }
        },
        "ATR": {
            "period": 14,
            "usage": "손절폭 계산, 변동성 측정",
            "application": {
                "stop_loss": "진입가 - 2*ATR",
                "position_size": "리스크 / ATR",
            }
        },
        "Keltner_Channel": {
            "params": {"ema": 20, "atr_mult": 2},
            "usage": "볼린저밴드 보조",
        },
        "Historical_Volatility": {
            "periods": [10, 20, 60],
            "usage": "실현 변동성",
        },
        "VIX_Correlation": {
            "usage": "시장 공포와의 상관관계",
        },
    },

    # =========================================================================
    # 거래량 지표 (Volume Indicators)
    # =========================================================================
    "volume": {
        "OBV": {
            "usage": "거래량 기반 추세 확인",
            "signals": {
                "obv_divergence": "가격-거래량 괴리 → 반전 가능",
            }
        },
        "VWAP": {
            "usage": "기관 매매 기준가",
            "signals": {
                "price_above_vwap": "당일 강세",
                "price_below_vwap": "당일 약세",
            }
        },
        "Volume_SMA": {
            "period": 20,
            "usage": "거래량 이상 탐지",
            "signals": {
                "volume > 2x_avg": "관심 급증 (뉴스 확인 필요)",
            }
        },
        "Accumulation_Distribution": {
            "usage": "매집/매도 압력",
        },
        "Chaikin_Money_Flow": {
            "period": 20,
            "usage": "자금 유입/유출",
        },
        "Volume_Profile": {
            "usage": "가격대별 거래량 (지지/저항)",
        },
    },

    # =========================================================================
    # 지지/저항 (Support/Resistance)
    # =========================================================================
    "levels": {
        "Pivot_Points": {
            "types": ["standard", "fibonacci", "camarilla"],
            "usage": "일중 지지/저항",
        },
        "Fibonacci_Retracement": {
            "levels": [0.236, 0.382, 0.5, 0.618, 0.786],
            "usage": "조정 목표 및 지지/저항",
        },
        "Fibonacci_Extension": {
            "levels": [1.0, 1.272, 1.618, 2.0, 2.618],
            "usage": "목표가 설정",
        },
        "Swing_High_Low": {
            "lookback": 20,
            "usage": "최근 고점/저점",
        },
        "Round_Numbers": {
            "usage": "심리적 지지/저항 (예: $100, $150)",
        },
    },

    # =========================================================================
    # 패턴 인식 (Pattern Recognition)
    # =========================================================================
    "patterns": {
        "candlestick": {
            "reversal": ["doji", "hammer", "shooting_star", "engulfing",
                        "morning_star", "evening_star", "harami"],
            "continuation": ["three_white_soldiers", "three_black_crows",
                           "rising_three", "falling_three"],
        },
        "chart_patterns": {
            "reversal": ["head_shoulders", "double_top", "double_bottom",
                        "triple_top", "triple_bottom", "rounding"],
            "continuation": ["flag", "pennant", "wedge", "rectangle",
                           "ascending_triangle", "descending_triangle"],
        },
    },
}
```

### 3.3 기본적 분석 지표 상세

```python
FUNDAMENTAL_INDICATORS = {
    # =========================================================================
    # 밸류에이션 (Valuation)
    # =========================================================================
    "valuation": {
        "PE_Ratio": {
            "formula": "Price / EPS",
            "interpretation": {
                "low": "< 15 (가치주 영역)",
                "normal": "15-25 (적정)",
                "high": "> 25 (성장 기대 반영)",
            },
            "caveats": "적자 기업은 N/A, 섹터별 차이 고려",
            "comparison": ["sector_median", "historical_avg", "market_avg"],
        },
        "Forward_PE": {
            "formula": "Price / Forward EPS",
            "usage": "미래 수익 기준 평가",
            "importance": "HIGH - 과거보다 미래 중요",
        },
        "PEG_Ratio": {
            "formula": "PE / EPS Growth Rate",
            "interpretation": {
                "< 1.0": "저평가 가능성",
                "1.0-2.0": "적정",
                "> 2.0": "고평가 가능성",
            },
            "usage": "성장주 평가에 필수",
        },
        "PB_Ratio": {
            "formula": "Price / Book Value",
            "interpretation": {
                "< 1.0": "자산가치 이하 (가치주)",
                "1.0-3.0": "일반적",
                "> 3.0": "무형자산/성장 반영",
            },
            "best_for": "금융주, 자산주",
        },
        "PS_Ratio": {
            "formula": "Price / Sales",
            "usage": "적자 기업 평가, 매출 성장 기업",
            "best_for": "성장주, 적자 기업",
        },
        "EV_EBITDA": {
            "formula": "Enterprise Value / EBITDA",
            "usage": "기업가치 평가의 표준",
            "interpretation": {
                "< 10": "저평가 가능",
                "10-15": "적정",
                "> 15": "고평가",
            },
        },
        "EV_Sales": {
            "formula": "Enterprise Value / Revenue",
            "usage": "매출 기준 기업가치",
        },
        "EV_FCF": {
            "formula": "Enterprise Value / Free Cash Flow",
            "usage": "현금흐름 기준 평가",
            "importance": "HIGH - 실질 가치",
        },
        "DCF_Fair_Value": {
            "method": "Discounted Cash Flow",
            "params": {
                "growth_rate": "애널리스트 추정치",
                "discount_rate": "WACC or 10%",
                "terminal_growth": "3%",
            },
            "usage": "내재가치 추정",
        },
    },

    # =========================================================================
    # 수익성 (Profitability)
    # =========================================================================
    "profitability": {
        "Gross_Margin": {
            "formula": "(Revenue - COGS) / Revenue",
            "usage": "원가 경쟁력",
            "good": "> 40%",
        },
        "Operating_Margin": {
            "formula": "Operating Income / Revenue",
            "usage": "영업 효율성",
            "good": "> 15%",
        },
        "Net_Margin": {
            "formula": "Net Income / Revenue",
            "usage": "최종 수익성",
            "good": "> 10%",
        },
        "ROE": {
            "formula": "Net Income / Shareholders Equity",
            "usage": "자기자본 효율",
            "interpretation": {
                "> 15%": "우수",
                "10-15%": "양호",
                "< 10%": "부진",
            },
            "dupont": "Net Margin × Asset Turnover × Leverage",
        },
        "ROA": {
            "formula": "Net Income / Total Assets",
            "usage": "총자산 효율",
            "good": "> 5%",
        },
        "ROIC": {
            "formula": "NOPAT / Invested Capital",
            "usage": "투하자본 수익률 (버핏 선호)",
            "good": "> WACC",
            "importance": "CRITICAL",
        },
        "ROC_Greenblatt": {
            "formula": "EBIT / (Net Working Capital + Net Fixed Assets)",
            "usage": "마법공식 구성요소",
        },
    },

    # =========================================================================
    # 성장성 (Growth)
    # =========================================================================
    "growth": {
        "Revenue_Growth": {
            "periods": ["yoy", "3y_cagr", "5y_cagr"],
            "good": "> 10% YoY",
        },
        "EPS_Growth": {
            "periods": ["yoy", "3y_cagr", "5y_cagr"],
            "good": "> 15% YoY",
        },
        "FCF_Growth": {
            "periods": ["yoy", "3y_cagr"],
            "usage": "현금흐름 성장",
        },
        "Book_Value_Growth": {
            "periods": ["yoy", "5y_cagr"],
            "usage": "내재가치 성장",
        },
        "Dividend_Growth": {
            "periods": ["yoy", "5y_cagr", "10y_cagr"],
            "usage": "배당 성장 (배당 귀족주)",
        },
        "Earnings_Surprise": {
            "last_4_quarters": [],
            "beat_rate": "실적 서프라이즈 비율",
            "importance": "주가 단기 방향에 영향",
        },
        "Estimate_Revisions": {
            "direction": "상향/하향 수정",
            "magnitude": "수정 폭",
            "importance": "애널리스트 기대 변화",
        },
    },

    # =========================================================================
    # 재무 건전성 (Financial Health)
    # =========================================================================
    "financial_health": {
        "Current_Ratio": {
            "formula": "Current Assets / Current Liabilities",
            "good": "> 1.5",
            "warning": "< 1.0",
        },
        "Quick_Ratio": {
            "formula": "(Current Assets - Inventory) / Current Liabilities",
            "good": "> 1.0",
        },
        "Debt_to_Equity": {
            "formula": "Total Debt / Shareholders Equity",
            "interpretation": {
                "< 0.5": "보수적",
                "0.5-1.0": "적정",
                "> 1.5": "높은 레버리지",
            },
        },
        "Debt_to_EBITDA": {
            "formula": "Total Debt / EBITDA",
            "good": "< 3.0",
            "warning": "> 5.0",
        },
        "Interest_Coverage": {
            "formula": "EBIT / Interest Expense",
            "good": "> 5.0",
            "warning": "< 2.0",
        },
        "Free_Cash_Flow": {
            "formula": "Operating Cash Flow - CapEx",
            "usage": "실질 잉여현금",
            "importance": "CRITICAL",
        },
        "FCF_Yield": {
            "formula": "FCF / Market Cap",
            "good": "> 5%",
        },
        "Altman_Z_Score": {
            "formula": "파산 확률 예측",
            "interpretation": {
                "> 3.0": "안전",
                "1.8-3.0": "주의",
                "< 1.8": "위험",
            },
        },
        "Piotroski_F_Score": {
            "range": "0-9",
            "usage": "재무 건전성 종합",
            "good": ">= 7",
        },
    },

    # =========================================================================
    # 배당 (Dividend)
    # =========================================================================
    "dividend": {
        "Dividend_Yield": {
            "formula": "Annual Dividend / Price",
            "usage": "배당 수익률",
        },
        "Payout_Ratio": {
            "formula": "Dividends / Net Income",
            "good": "30-60%",
            "warning": "> 80%",
        },
        "Dividend_Coverage": {
            "formula": "EPS / DPS",
            "good": "> 2.0",
        },
        "Years_of_Growth": {
            "usage": "연속 배당 성장 연수",
            "aristocrat": ">= 25년",
            "king": ">= 50년",
        },
        "Ex_Dividend_Date": {
            "usage": "배당락일 추적",
        },
    },

    # =========================================================================
    # 퀄리티 스코어 (Quality Score)
    # =========================================================================
    "quality_composite": {
        "factors": [
            "ROIC_stability",           # ROIC 안정성
            "earnings_quality",          # 이익의 질 (현금흐름 vs 회계이익)
            "balance_sheet_strength",    # 재무구조
            "margin_stability",          # 마진 안정성
            "capital_allocation",        # 자본 배분 효율
        ],
        "scoring": "각 요소 0-20점, 총 100점",
    },
}
```

### 3.4 센티멘트 분석 지표 상세

```python
SENTIMENT_INDICATORS = {
    # =========================================================================
    # 뉴스 센티멘트 (News Sentiment)
    # =========================================================================
    "news": {
        "headline_sentiment": {
            "source": "Finnhub, NewsAPI",
            "method": "NLP 감성 분석",
            "score_range": "-1.0 ~ +1.0",
            "aggregation": "24시간 가중 평균",
        },
        "news_volume": {
            "metric": "뉴스 기사 수",
            "comparison": "20일 평균 대비",
            "interpretation": {
                "spike": "중요 이벤트 발생",
                "low": "관심 저조",
            },
        },
        "topic_analysis": {
            "categories": ["earnings", "product", "management",
                         "legal", "m&a", "macro"],
            "risk_keywords": ["lawsuit", "investigation", "recall",
                            "bankruptcy", "fraud", "downgrade"],
        },
    },

    # =========================================================================
    # 애널리스트 센티멘트 (Analyst Sentiment)
    # =========================================================================
    "analyst": {
        "consensus_rating": {
            "scale": "Strong Buy (5) → Strong Sell (1)",
            "usage": "시장 기대 수준",
        },
        "rating_distribution": {
            "buy_pct": "매수 추천 비율",
            "hold_pct": "중립 비율",
            "sell_pct": "매도 추천 비율",
        },
        "target_price": {
            "mean": "평균 목표가",
            "high": "최고 목표가",
            "low": "최저 목표가",
            "upside": "(목표가 - 현재가) / 현재가",
        },
        "rating_changes": {
            "upgrades_30d": "최근 30일 상향",
            "downgrades_30d": "최근 30일 하향",
            "net_change": "순 변경",
        },
        "estimate_revisions": {
            "eps_revision_1m": "1개월 EPS 추정 변화",
            "eps_revision_3m": "3개월 EPS 추정 변화",
            "direction": "상향/하향 추세",
        },
    },

    # =========================================================================
    # 기관/내부자 (Institutional/Insider)
    # =========================================================================
    "institutional": {
        "ownership_pct": {
            "metric": "기관 보유 비율",
            "good": "40-80%",
        },
        "ownership_change": {
            "qoq": "분기 대비 변화",
            "interpretation": {
                "increasing": "기관 매집",
                "decreasing": "기관 이탈",
            },
        },
        "top_holders": {
            "data": "상위 10개 기관",
            "changes": "보유 변화",
        },
        "insider_transactions": {
            "buys_3m": "3개월 내부자 매수",
            "sells_3m": "3개월 내부자 매도",
            "net_value": "순 매수 금액",
            "significance": {
                "ceo_buy": "매우 긍정적",
                "multiple_insiders_buy": "긍정적",
                "10b5_1_sales": "계획된 매도 (중립)",
            },
        },
    },

    # =========================================================================
    # 공매도 (Short Interest)
    # =========================================================================
    "short_interest": {
        "short_pct_float": {
            "metric": "유통주식 대비 공매도 비율",
            "interpretation": {
                "< 5%": "정상",
                "5-10%": "주의",
                "10-20%": "높음",
                "> 20%": "매우 높음 (숏스퀴즈 가능)",
            },
        },
        "days_to_cover": {
            "formula": "Short Interest / Avg Daily Volume",
            "warning": "> 5일",
        },
        "short_interest_change": {
            "mom": "월간 변화",
            "trend": "증가/감소 추세",
        },
    },

    # =========================================================================
    # 옵션 시장 (Options Market)
    # =========================================================================
    "options": {
        "put_call_ratio": {
            "interpretation": {
                "< 0.7": "낙관적 (콜 우세)",
                "0.7-1.0": "중립",
                "> 1.0": "비관적 (풋 우세)",
            },
            "contrarian": "극단값에서 역발상",
        },
        "implied_volatility": {
            "vs_historical": "내재 vs 실현 변동성",
            "iv_percentile": "IV 백분위",
            "interpretation": {
                "high_iv": "불확실성 높음 (실적 전 등)",
                "iv_crush": "이벤트 후 IV 급락 예상",
            },
        },
        "unusual_activity": {
            "large_trades": "대규모 옵션 거래",
            "sweep_orders": "스윕 주문",
            "interpretation": "스마트 머니 움직임",
        },
        "max_pain": {
            "definition": "만기일 최대 손실 가격",
            "usage": "단기 가격 자석",
        },
    },

    # =========================================================================
    # 시장 심리 지표 (Market Sentiment)
    # =========================================================================
    "market_sentiment": {
        "fear_greed_index": {
            "source": "CNN Fear & Greed",
            "range": "0 (극도 공포) - 100 (극도 탐욕)",
            "contrarian_signals": {
                "< 20": "극도 공포 → 매수 기회",
                "> 80": "극도 탐욕 → 주의",
            },
        },
        "aaii_sentiment": {
            "source": "AAII Investor Sentiment Survey",
            "metrics": ["bullish_pct", "bearish_pct", "neutral_pct"],
            "bull_bear_spread": "강세 - 약세 비율",
        },
        "vix": {
            "interpretation": {
                "< 15": "안정 (complacency 주의)",
                "15-20": "정상",
                "20-30": "불안",
                "> 30": "공포 (반등 기회)",
                "> 40": "패닉",
            },
        },
        "vix_term_structure": {
            "contango": "정상 (원월물 > 근월물)",
            "backwardation": "공포 심화",
        },
    },

    # =========================================================================
    # 자금 흐름 (Fund Flows)
    # =========================================================================
    "fund_flows": {
        "etf_flows": {
            "spy_flow": "S&P 500 ETF 자금 흐름",
            "sector_flows": "섹터 ETF 흐름",
            "interpretation": "기관 자금 방향",
        },
        "margin_debt": {
            "level": "마진 부채 수준",
            "change": "월간 변화",
            "warning": "사상 최고 수준 주의",
        },
        "money_market_funds": {
            "level": "대기 자금 규모",
            "interpretation": "높으면 잠재 매수세",
        },
    },
}
```

### 3.5 거시경제 지표 상세

```python
MACRO_INDICATORS = {
    # =========================================================================
    # 미국 경제 지표 (US Economic Indicators)
    # =========================================================================
    "us_economy": {
        # ----- 금리/통화정책 -----
        "fed_funds_rate": {
            "source": "FRED: FEDFUNDS",
            "frequency": "FOMC 회의 (연 8회)",
            "impact": {
                "hike": "주식 약세, 채권 약세, 달러 강세",
                "cut": "주식 강세, 채권 강세, 달러 약세",
            },
            "importance": "CRITICAL",
        },
        "fed_funds_futures": {
            "source": "CME FedWatch",
            "usage": "금리 인상/인하 확률",
        },
        "fomc_dot_plot": {
            "usage": "연준 위원들 금리 전망",
        },
        "fed_balance_sheet": {
            "source": "FRED: WALCL",
            "usage": "양적완화/긴축 규모",
            "impact": {
                "expanding": "유동성 증가 → 주식 강세",
                "shrinking": "유동성 감소 → 주식 약세",
            },
        },

        # ----- 인플레이션 -----
        "cpi": {
            "source": "FRED: CPIAUCSL",
            "frequency": "월간",
            "metrics": ["yoy", "mom", "core_yoy"],
            "target": "2%",
            "impact": {
                "above_target": "금리 인상 압력",
                "below_target": "금리 인하 여지",
            },
            "importance": "CRITICAL",
        },
        "pce": {
            "source": "FRED: PCEPI",
            "usage": "연준 선호 물가 지표",
            "importance": "CRITICAL",
        },
        "inflation_expectations": {
            "source": "FRED: T5YIE (5년 기대인플레이션)",
            "usage": "시장의 인플레이션 전망",
        },

        # ----- 고용 -----
        "nonfarm_payrolls": {
            "source": "FRED: PAYEMS",
            "frequency": "월간 (첫째 금요일)",
            "good": "> 200K",
            "impact": "강하면 금리 인상, 약하면 인하",
            "importance": "HIGH",
        },
        "unemployment_rate": {
            "source": "FRED: UNRATE",
            "natural_rate": "~4%",
            "impact": {
                "rising": "경기 침체 우려",
                "falling": "경기 확장",
            },
        },
        "jobless_claims": {
            "source": "FRED: ICSA",
            "frequency": "주간",
            "usage": "고용 시장 선행 지표",
            "warning": "> 300K 지속",
        },
        "jolts": {
            "source": "FRED: JTSJOL",
            "usage": "구인 건수 (노동 수요)",
        },

        # ----- 성장 -----
        "gdp": {
            "source": "FRED: GDP",
            "frequency": "분기",
            "metrics": ["real_gdp_growth", "nominal_gdp"],
            "recession": "2분기 연속 마이너스",
            "importance": "HIGH",
        },
        "gdp_now": {
            "source": "Atlanta Fed GDPNow",
            "usage": "실시간 GDP 추정",
        },

        # ----- 소비/생산 -----
        "retail_sales": {
            "source": "FRED: RSAFS",
            "frequency": "월간",
            "usage": "소비 동향",
        },
        "consumer_confidence": {
            "source": "Conference Board",
            "frequency": "월간",
            "usage": "소비 심리",
        },
        "michigan_sentiment": {
            "source": "University of Michigan",
            "frequency": "월간",
            "usage": "소비자 심리 + 인플레이션 기대",
        },
        "industrial_production": {
            "source": "FRED: INDPRO",
            "usage": "제조업 생산",
        },

        # ----- 선행 지표 -----
        "ism_manufacturing": {
            "source": "ISM",
            "frequency": "월간 (첫째 영업일)",
            "threshold": 50,
            "interpretation": {
                "> 50": "확장",
                "< 50": "수축",
            },
            "importance": "HIGH",
        },
        "ism_services": {
            "source": "ISM",
            "frequency": "월간 (셋째 영업일)",
            "importance": "HIGH (서비스 = 미국 경제 70%)",
        },
        "pmi_flash": {
            "source": "S&P Global",
            "usage": "ISM 선행 지표",
        },
        "leading_economic_index": {
            "source": "Conference Board LEI",
            "usage": "경기 선행 지표 종합",
        },
    },

    # =========================================================================
    # 금리/채권 (Rates/Bonds)
    # =========================================================================
    "rates": {
        "treasury_yields": {
            "2y": {"source": "FRED: DGS2", "usage": "단기 금리 기대"},
            "5y": {"source": "FRED: DGS5"},
            "10y": {"source": "FRED: DGS10", "usage": "장기 금리 벤치마크"},
            "30y": {"source": "FRED: DGS30", "usage": "초장기 금리"},
        },
        "yield_curve": {
            "10y_2y_spread": {
                "source": "FRED: T10Y2Y",
                "interpretation": {
                    "positive": "정상",
                    "flat": "경기 둔화 신호",
                    "inverted": "경기 침체 선행 신호 (6-18개월)",
                },
                "importance": "CRITICAL",
            },
            "10y_3m_spread": {
                "usage": "연준 선호 지표",
            },
        },
        "real_rates": {
            "tips_10y": {"source": "FRED: DFII10"},
            "interpretation": {
                "negative": "실질 금리 음수 → 주식 유리",
                "positive_high": "주식 불리",
            },
        },
        "credit_spreads": {
            "investment_grade": "IG 스프레드",
            "high_yield": "HY 스프레드",
            "interpretation": {
                "widening": "신용 위험 증가 → Risk-Off",
                "tightening": "신용 위험 감소 → Risk-On",
            },
        },
    },

    # =========================================================================
    # 시장 지수 (Market Indices)
    # =========================================================================
    "indices": {
        "sp500": {
            "symbol": "^GSPC",
            "usage": "미국 대형주 벤치마크",
            "levels": {
                "above_200sma": "장기 상승 추세",
                "below_200sma": "장기 하락 추세",
            },
        },
        "nasdaq": {
            "symbol": "^IXIC",
            "usage": "기술주 벤치마크",
        },
        "dow": {
            "symbol": "^DJI",
            "usage": "우량주 벤치마크",
        },
        "russell2000": {
            "symbol": "^RUT",
            "usage": "소형주 벤치마크",
            "interpretation": "경기 민감",
        },
        "vix": {
            "symbol": "^VIX",
            "usage": "공포 지수",
            "importance": "CRITICAL",
        },
        "move_index": {
            "usage": "채권 변동성",
        },
    },

    # =========================================================================
    # 섹터 동향 (Sector Trends)
    # =========================================================================
    "sectors": {
        "etfs": {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLV": "Healthcare",
            "XLE": "Energy",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLI": "Industrials",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLC": "Communication Services",
        },
        "analysis": {
            "relative_strength": "SPY 대비 상대 강도",
            "rotation": "섹터 순환 분석",
            "economic_cycle": {
                "early_cycle": ["XLF", "XLY", "XLI"],
                "mid_cycle": ["XLK", "XLC"],
                "late_cycle": ["XLE", "XLB"],
                "recession": ["XLP", "XLV", "XLU"],
            },
        },
    },

    # =========================================================================
    # 글로벌 (Global)
    # =========================================================================
    "global": {
        "dxy": {
            "usage": "달러 인덱스",
            "impact": {
                "strong_dollar": "다국적 기업 실적 압박, EM 부담",
                "weak_dollar": "다국적 기업 유리, EM 유리",
            },
        },
        "gold": {
            "symbol": "GC=F",
            "usage": "안전자산, 인플레이션 헤지",
        },
        "oil_wti": {
            "symbol": "CL=F",
            "usage": "에너지 섹터, 인플레이션",
        },
        "copper": {
            "symbol": "HG=F",
            "usage": "경기 선행 지표 (Dr. Copper)",
        },
        "bitcoin": {
            "symbol": "BTC-USD",
            "usage": "위험 선호 지표",
        },
        "global_indices": {
            "stoxx600": "유럽",
            "nikkei": "일본",
            "shanghai": "중국",
            "kospi": "한국",
        },
    },

    # =========================================================================
    # 이벤트 캘린더 (Event Calendar)
    # =========================================================================
    "calendar": {
        "fomc_meetings": {
            "frequency": "연 8회",
            "importance": "CRITICAL",
            "trading_rule": "발표 당일 변동성 주의",
        },
        "cpi_release": {
            "frequency": "월간 (10-15일)",
            "importance": "CRITICAL",
        },
        "jobs_report": {
            "frequency": "월간 (첫째 금요일)",
            "importance": "HIGH",
        },
        "earnings_season": {
            "timing": "분기 중순 (1월, 4월, 7월, 10월)",
            "importance": "HIGH",
        },
        "options_expiration": {
            "monthly": "셋째 금요일",
            "quarterly": "3월, 6월, 9월, 12월 (Triple Witching)",
            "impact": "변동성 증가",
        },
    },
}
```

---

## Part 4: AI 판단 시스템

### 4.1 종합 점수 시스템

```python
class ComprehensiveScorer:
    """
    각 분석 축의 점수를 종합하여 최종 투자 점수 산출
    """

    WEIGHTS = {
        "technical": 0.25,      # 기술적 분석 25%
        "fundamental": 0.30,    # 기본적 분석 30%
        "sentiment": 0.20,      # 센티멘트 20%
        "macro": 0.15,          # 거시경제 15%
        "quality": 0.10,        # 퀄리티 10%
    }

    SCORE_INTERPRETATION = {
        (80, 100): {"action": "STRONG_BUY", "confidence": "HIGH"},
        (60, 80): {"action": "BUY", "confidence": "MEDIUM-HIGH"},
        (40, 60): {"action": "HOLD", "confidence": "NEUTRAL"},
        (20, 40): {"action": "REDUCE", "confidence": "MEDIUM"},
        (0, 20): {"action": "SELL", "confidence": "HIGH"},
        (-100, 0): {"action": "AVOID", "confidence": "HIGH"},
    }

    def calculate_composite_score(self, symbol: str) -> dict:
        """종합 점수 계산"""
        scores = {
            "technical": self.technical_analyzer.score(symbol),    # -100 ~ +100
            "fundamental": self.fundamental_analyzer.score(symbol),
            "sentiment": self.sentiment_analyzer.score(symbol),
            "macro": self.macro_analyzer.score(),  # 시장 전체
            "quality": self.quality_analyzer.score(symbol),
        }

        # 가중 평균
        weighted_score = sum(
            scores[key] * self.WEIGHTS[key]
            for key in scores
        )

        # 점수 조정 (극단적 음수 요소 있으면 페널티)
        adjusted_score = self._apply_adjustments(weighted_score, scores)

        return {
            "symbol": symbol,
            "composite_score": adjusted_score,
            "component_scores": scores,
            "interpretation": self._interpret(adjusted_score),
            "confidence": self._calculate_confidence(scores),
            "risks": self._identify_risks(scores),
        }

    def _apply_adjustments(self, score: float, components: dict) -> float:
        """점수 조정"""
        adjusted = score

        # 기본적 분석이 매우 부정적이면 페널티
        if components["fundamental"] < -50:
            adjusted *= 0.7

        # 거시경제가 매우 부정적이면 전체 하향
        if components["macro"] < -30:
            adjusted -= 10

        # 기술적 + 센티멘트 동시 부정적이면 추가 하향
        if components["technical"] < -30 and components["sentiment"] < -30:
            adjusted -= 15

        return max(min(adjusted, 100), -100)

    def _calculate_confidence(self, components: dict) -> float:
        """확신도 계산 (0-1)"""
        # 모든 지표가 같은 방향이면 높은 확신도
        signs = [1 if v > 0 else -1 if v < 0 else 0 for v in components.values()]
        agreement = abs(sum(signs)) / len(signs)

        # 개별 점수의 절대값이 크면 확신도 증가
        magnitude = sum(abs(v) for v in components.values()) / (len(components) * 100)

        return (agreement * 0.6 + magnitude * 0.4)
```

### 4.2 AI 프롬프트 시스템

```python
# =========================================================================
# 시스템 프롬프트 (Master Prompt)
# =========================================================================

MASTER_SYSTEM_PROMPT = """
You are an elite portfolio manager and investment analyst with expertise in:
- Quantitative analysis and factor investing
- Fundamental analysis (Buffett/Munger style value investing)
- Technical analysis and market structure
- Macro economics and market cycles
- Behavioral finance and sentiment analysis

## YOUR INVESTMENT PHILOSOPHY

### Core Principles
1. **Capital Preservation First**: Never take a position that could result in permanent capital loss
2. **Margin of Safety**: Only invest when price is significantly below intrinsic value
3. **Quality Over Quantity**: Prefer fewer, high-conviction positions
4. **Long-term Thinking**: Base decisions on 3-5 year outlook, not short-term noise
5. **Contrarian When Warranted**: Be greedy when others are fearful (with justification)

### Decision Framework
1. **Is this a quality business?** (Moat, ROIC, Management)
2. **Is it undervalued?** (Margin of Safety > 20%)
3. **What could go wrong?** (Identify and quantify risks)
4. **Does it fit the portfolio?** (Correlation, sector exposure)
5. **What's the catalyst?** (Why will the market recognize value?)

### Risk Management Rules
- Never exceed 5% in single position (8% max for highest conviction)
- Total sector exposure < 30%
- Always have stop-loss plan before entry
- Cut losses at -7% individual, -5% portfolio weekly
- Add to winners cautiously, never average down blindly

### Red Flags (Automatic Rejection)
- Accounting irregularities or restatements
- Excessive insider selling
- Deteriorating fundamentals with no catalyst for reversal
- Excessive leverage during rate hike cycle
- Negative free cash flow with no path to profitability

## YOUR ANALYTICAL APPROACH

### For BUY Decisions, Require:
1. At least 3 of 4 analysis pillars showing positive signals
2. No major red flags in any pillar
3. Identifiable margin of safety (> 15%)
4. Clear thesis that can be articulated in 2-3 sentences
5. Defined exit criteria (both profit target and stop-loss)

### For SELL Decisions, Consider:
1. Original thesis no longer valid
2. Better opportunity elsewhere (opportunity cost)
3. Position size grew too large
4. Risk/reward no longer favorable
5. Stop-loss triggered

### Position Sizing Logic
- Base position: 2-3% of portfolio
- Higher conviction (score > 80, all pillars aligned): Up to 5%
- Lower conviction or higher volatility: 1-2%
- Use Kelly Criterion as upper bound, apply Half-Kelly

## OUTPUT REQUIREMENTS

Always structure your analysis as:
1. **Summary**: 2-3 sentence investment thesis
2. **Composite Score**: Weighted score with breakdown
3. **Decision**: BUY/SELL/HOLD with specific action
4. **Position Sizing**: Exact percentage and rationale
5. **Entry/Exit**: Specific prices for entry, stop-loss, targets
6. **Risks**: Top 3 risks with mitigation strategies
7. **Monitoring**: What to watch for thesis validation/invalidation

Use the trading_decision tool to submit your final recommendation.
"""

# =========================================================================
# 종목 분석 프롬프트
# =========================================================================

def build_stock_analysis_prompt(symbol: str, data: dict) -> str:
    return f"""
═══════════════════════════════════════════════════════════════════════════
                    STOCK ANALYSIS REQUEST: {symbol}
═══════════════════════════════════════════════════════════════════════════

## 1. COMPANY OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {data['company']['name']}
Sector: {data['company']['sector']}
Industry: {data['company']['industry']}
Market Cap: ${data['company']['market_cap']:,.0f}
Description: {data['company']['description'][:500]}...

## 2. TECHNICAL ANALYSIS (Weight: 25%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Price Action
- Current Price: ${data['technical']['price']:.2f}
- 52-Week Range: ${data['technical']['52w_low']:.2f} - ${data['technical']['52w_high']:.2f}
- % from 52W High: {data['technical']['pct_from_high']:.1f}%
- % from 52W Low: {data['technical']['pct_from_low']:.1f}%

### Moving Averages
- Price vs SMA20: {data['technical']['vs_sma20']:+.1f}%
- Price vs SMA50: {data['technical']['vs_sma50']:+.1f}%
- Price vs SMA200: {data['technical']['vs_sma200']:+.1f}%
- SMA Alignment: {data['technical']['sma_alignment']}  (bullish = 20>50>200)
- Golden/Death Cross: {data['technical']['cross_signal']}

### Momentum
- RSI(14): {data['technical']['rsi']:.1f} ({data['technical']['rsi_signal']})
- MACD: {data['technical']['macd']['value']:.2f} (Signal: {data['technical']['macd']['signal']:.2f})
- MACD Histogram: {data['technical']['macd']['histogram']:.2f}
- Stochastic %K/%D: {data['technical']['stoch_k']:.1f}/{data['technical']['stoch_d']:.1f}

### Volatility
- ATR(14): ${data['technical']['atr']:.2f} ({data['technical']['atr_pct']:.1f}% of price)
- Bollinger Band Position: {data['technical']['bb_position']} (0=lower, 0.5=middle, 1=upper)
- 20-Day Volatility: {data['technical']['volatility_20d']:.1f}%

### Volume
- Current Volume: {data['technical']['volume']:,}
- vs 20-Day Avg: {data['technical']['volume_ratio']:.1f}x
- OBV Trend: {data['technical']['obv_trend']}

### Key Levels
- Support: ${data['technical']['support_1']:.2f}, ${data['technical']['support_2']:.2f}
- Resistance: ${data['technical']['resistance_1']:.2f}, ${data['technical']['resistance_2']:.2f}
- Fibonacci Levels: {data['technical']['fib_levels']}

### Patterns Detected
{data['technical']['patterns']}

### TECHNICAL SCORE: {data['technical']['score']:+.0f}/100
Signal: {data['technical']['signal']}

## 3. FUNDAMENTAL ANALYSIS (Weight: 30%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Valuation
| Metric | Value | Sector Median | vs Sector |
|--------|-------|---------------|-----------|
| P/E (TTM) | {data['fundamental']['pe']:.1f} | {data['fundamental']['sector_pe']:.1f} | {data['fundamental']['pe_vs_sector']:+.0f}% |
| Forward P/E | {data['fundamental']['fwd_pe']:.1f} | {data['fundamental']['sector_fwd_pe']:.1f} | {data['fundamental']['fwd_pe_vs_sector']:+.0f}% |
| PEG Ratio | {data['fundamental']['peg']:.2f} | - | - |
| P/B | {data['fundamental']['pb']:.2f} | {data['fundamental']['sector_pb']:.2f} | {data['fundamental']['pb_vs_sector']:+.0f}% |
| P/S | {data['fundamental']['ps']:.2f} | {data['fundamental']['sector_ps']:.2f} | {data['fundamental']['ps_vs_sector']:+.0f}% |
| EV/EBITDA | {data['fundamental']['ev_ebitda']:.1f} | {data['fundamental']['sector_ev_ebitda']:.1f} | {data['fundamental']['ev_ebitda_vs_sector']:+.0f}% |
| EV/FCF | {data['fundamental']['ev_fcf']:.1f} | - | - |

### Profitability
| Metric | Value | 5Y Avg | Trend |
|--------|-------|--------|-------|
| Gross Margin | {data['fundamental']['gross_margin']:.1f}% | {data['fundamental']['gross_margin_5y']:.1f}% | {data['fundamental']['gross_margin_trend']} |
| Operating Margin | {data['fundamental']['op_margin']:.1f}% | {data['fundamental']['op_margin_5y']:.1f}% | {data['fundamental']['op_margin_trend']} |
| Net Margin | {data['fundamental']['net_margin']:.1f}% | {data['fundamental']['net_margin_5y']:.1f}% | {data['fundamental']['net_margin_trend']} |
| ROE | {data['fundamental']['roe']:.1f}% | {data['fundamental']['roe_5y']:.1f}% | {data['fundamental']['roe_trend']} |
| ROIC | {data['fundamental']['roic']:.1f}% | {data['fundamental']['roic_5y']:.1f}% | {data['fundamental']['roic_trend']} |

### Growth
| Metric | YoY | 3Y CAGR | 5Y CAGR |
|--------|-----|---------|---------|
| Revenue | {data['fundamental']['rev_yoy']:+.1f}% | {data['fundamental']['rev_3y']:+.1f}% | {data['fundamental']['rev_5y']:+.1f}% |
| EPS | {data['fundamental']['eps_yoy']:+.1f}% | {data['fundamental']['eps_3y']:+.1f}% | {data['fundamental']['eps_5y']:+.1f}% |
| FCF | {data['fundamental']['fcf_yoy']:+.1f}% | {data['fundamental']['fcf_3y']:+.1f}% | - |

### Financial Health
- Current Ratio: {data['fundamental']['current_ratio']:.2f}
- Debt/Equity: {data['fundamental']['debt_equity']:.2f}
- Debt/EBITDA: {data['fundamental']['debt_ebitda']:.1f}x
- Interest Coverage: {data['fundamental']['interest_coverage']:.1f}x
- Free Cash Flow: ${data['fundamental']['fcf']:,.0f}M
- FCF Yield: {data['fundamental']['fcf_yield']:.1f}%
- Altman Z-Score: {data['fundamental']['z_score']:.2f} ({data['fundamental']['z_score_interpretation']})
- Piotroski F-Score: {data['fundamental']['f_score']}/9

### Dividend
- Yield: {data['fundamental']['div_yield']:.2f}%
- Payout Ratio: {data['fundamental']['payout_ratio']:.0f}%
- 5Y Dividend CAGR: {data['fundamental']['div_growth_5y']:+.1f}%
- Years of Consecutive Growth: {data['fundamental']['div_years']}

### Earnings Quality
- Next Earnings Date: {data['fundamental']['next_earnings']}
- Last 4 Quarters Surprise: {data['fundamental']['earnings_surprises']}
- Analyst EPS Revisions (30D): {data['fundamental']['eps_revisions']}

### Fair Value Estimate
- DCF Fair Value: ${data['fundamental']['dcf_value']:.2f}
- Current Price: ${data['technical']['price']:.2f}
- Margin of Safety: {data['fundamental']['margin_of_safety']:+.1f}%

### FUNDAMENTAL SCORE: {data['fundamental']['score']:+.0f}/100
Signal: {data['fundamental']['signal']}

## 4. SENTIMENT ANALYSIS (Weight: 20%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### News Sentiment (24h)
- Sentiment Score: {data['sentiment']['news_score']:.2f} (-1 to +1)
- News Volume: {data['sentiment']['news_volume']} (vs avg: {data['sentiment']['news_volume_ratio']:.1f}x)
- Key Headlines:
{data['sentiment']['headlines']}

### Analyst Ratings
- Consensus: {data['sentiment']['consensus']} ({data['sentiment']['consensus_score']:.1f}/5)
- Distribution: Buy {data['sentiment']['buy_pct']}% | Hold {data['sentiment']['hold_pct']}% | Sell {data['sentiment']['sell_pct']}%
- Target Price (Mean): ${data['sentiment']['target_mean']:.2f} ({data['sentiment']['target_upside']:+.1f}% upside)
- Target Price Range: ${data['sentiment']['target_low']:.2f} - ${data['sentiment']['target_high']:.2f}
- Recent Changes: {data['sentiment']['rating_changes']}

### Institutional Activity
- Institutional Ownership: {data['sentiment']['inst_ownership']:.1f}%
- QoQ Change: {data['sentiment']['inst_change']:+.1f}%
- Notable Moves: {data['sentiment']['inst_notable']}

### Insider Activity (90 Days)
- Insider Buys: {data['sentiment']['insider_buys']} (${data['sentiment']['insider_buy_value']:,.0f})
- Insider Sells: {data['sentiment']['insider_sells']} (${data['sentiment']['insider_sell_value']:,.0f})
- Net: {data['sentiment']['insider_net']}

### Short Interest
- Short % of Float: {data['sentiment']['short_pct']:.1f}%
- Days to Cover: {data['sentiment']['days_to_cover']:.1f}
- Short Interest Change (MoM): {data['sentiment']['short_change']:+.1f}%

### Options Activity
- Put/Call Ratio: {data['sentiment']['put_call']:.2f}
- IV Percentile: {data['sentiment']['iv_percentile']:.0f}%
- Unusual Activity: {data['sentiment']['unusual_options']}

### SENTIMENT SCORE: {data['sentiment']['score']:+.0f}/100
Signal: {data['sentiment']['signal']}

## 5. MACRO ENVIRONMENT (Weight: 15%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Market Regime
- Current Regime: {data['macro']['regime']}
- S&P 500 Trend: {data['macro']['sp500_trend']}
- VIX Level: {data['macro']['vix']:.1f} ({data['macro']['vix_signal']})

### Economic Indicators
- Fed Funds Rate: {data['macro']['fed_rate']:.2f}%
- Rate Outlook: {data['macro']['rate_outlook']}
- CPI YoY: {data['macro']['cpi']:.1f}%
- Unemployment: {data['macro']['unemployment']:.1f}%
- Yield Curve (10Y-2Y): {data['macro']['yield_curve']:+.2f}%

### Sector Analysis
- {symbol}'s Sector ({data['company']['sector']}): {data['macro']['sector_trend']}
- Relative Strength vs SPY: {data['macro']['sector_rs']:+.1f}%
- Sector Rotation Phase: {data['macro']['rotation_phase']}

### Risk Assessment
- Market Risk Level: {data['macro']['market_risk']}
- Sector-Specific Risk: {data['macro']['sector_risk']}

### MACRO SCORE: {data['macro']['score']:+.0f}/100
Signal: {data['macro']['signal']}

## 6. QUALITY ASSESSMENT (Weight: 10%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Competitive Moat
- Moat Rating: {data['quality']['moat']}
- Moat Sources: {data['quality']['moat_sources']}

### Management Quality
- Capital Allocation: {data['quality']['capital_allocation']}
- Insider Alignment: {data['quality']['insider_alignment']}
- Track Record: {data['quality']['mgmt_track_record']}

### Business Quality
- Revenue Predictability: {data['quality']['rev_predictability']}
- Customer Concentration: {data['quality']['customer_concentration']}
- Cyclicality: {data['quality']['cyclicality']}

### QUALITY SCORE: {data['quality']['score']:+.0f}/100

## 7. PORTFOLIO CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Current Portfolio
{data['portfolio']['holdings_summary']}

### Correlation Analysis
- Correlation with Portfolio: {data['portfolio']['correlation']:.2f}
- Sector Exposure if Added: {data['portfolio']['sector_exposure_new']:.1f}%

### Risk Budget
- Current Portfolio Risk: {data['portfolio']['current_risk']:.1f}%
- Risk Budget Available: {data['portfolio']['risk_budget']:.1f}%

## 8. RECENT PERFORMANCE & TRADES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
### Previous Trades in {symbol}
{data['history']['previous_trades']}

### System Performance
- Win Rate (30D): {data['history']['win_rate']:.0f}%
- Avg Return per Trade: {data['history']['avg_return']:+.1f}%
- Sharpe Ratio (30D): {data['history']['sharpe']:.2f}

═══════════════════════════════════════════════════════════════════════════
                              COMPOSITE ANALYSIS
═══════════════════════════════════════════════════════════════════════════

### WEIGHTED COMPOSITE SCORE
| Pillar | Score | Weight | Weighted |
|--------|-------|--------|----------|
| Technical | {data['technical']['score']:+.0f} | 25% | {data['technical']['score']*0.25:+.1f} |
| Fundamental | {data['fundamental']['score']:+.0f} | 30% | {data['fundamental']['score']*0.30:+.1f} |
| Sentiment | {data['sentiment']['score']:+.0f} | 20% | {data['sentiment']['score']*0.20:+.1f} |
| Macro | {data['macro']['score']:+.0f} | 15% | {data['macro']['score']*0.15:+.1f} |
| Quality | {data['quality']['score']:+.0f} | 10% | {data['quality']['score']*0.10:+.1f} |
| **TOTAL** | - | 100% | **{data['composite_score']:+.1f}** |

═══════════════════════════════════════════════════════════════════════════

Based on all the above analysis, provide your trading recommendation.
Remember: Capital preservation is paramount. When in doubt, stay out.

Use the trading_decision tool to submit your recommendation.
"""
```

### 4.3 의사결정 검증 시스템

```python
class DecisionValidator:
    """AI 결정의 논리적 일관성 및 리스크 검증"""

    def validate(self, decision: TradingDecision, context: dict) -> ValidationResult:
        """다단계 검증"""
        checks = []

        # 1. 논리 일관성 검증
        checks.append(self._check_logic_consistency(decision, context))

        # 2. 점수-행동 일관성
        checks.append(self._check_score_action_alignment(decision, context))

        # 3. 리스크 한도 검증
        checks.append(self._check_risk_limits(decision, context))

        # 4. 포트폴리오 적합성
        checks.append(self._check_portfolio_fit(decision, context))

        # 5. 시장 상황 적합성
        checks.append(self._check_market_conditions(decision, context))

        # 6. 과거 유사 결정 성과
        checks.append(self._check_historical_performance(decision, context))

        # 종합 판정
        passed = all(c["passed"] for c in checks)
        warnings = [c["warning"] for c in checks if c.get("warning")]

        return ValidationResult(
            passed=passed,
            checks=checks,
            warnings=warnings,
            recommendation="PROCEED" if passed else "REVIEW_REQUIRED"
        )

    def _check_logic_consistency(self, decision, context) -> dict:
        """논리 일관성 체크"""
        issues = []

        # BUY인데 점수가 낮으면
        if decision.decision == "buy" and context["composite_score"] < 40:
            issues.append(f"BUY decision with low score ({context['composite_score']})")

        # SELL인데 점수가 높으면
        if decision.decision == "sell" and context["composite_score"] > 60:
            issues.append(f"SELL decision with high score ({context['composite_score']})")

        # 높은 확신도인데 점수가 중립이면
        if decision.confidence > 8 and 30 < context["composite_score"] < 70:
            issues.append("High confidence with neutral score")

        return {
            "check": "logic_consistency",
            "passed": len(issues) == 0,
            "issues": issues,
        }

    def _check_risk_limits(self, decision, context) -> dict:
        """리스크 한도 체크"""
        issues = []
        portfolio = context["portfolio"]

        # 포지션 사이즈 체크
        proposed_weight = decision.percentage / 100
        if proposed_weight > 0.08:
            issues.append(f"Position size {proposed_weight:.1%} exceeds max 8%")

        # 섹터 집중도 체크
        sector = context["company"]["sector"]
        current_sector_weight = portfolio["sector_weights"].get(sector, 0)
        new_sector_weight = current_sector_weight + proposed_weight

        if new_sector_weight > 0.30:
            issues.append(f"Sector exposure {new_sector_weight:.1%} exceeds max 30%")

        # 상관관계 체크
        if context["portfolio"]["correlation"] > 0.7:
            issues.append(f"High correlation {context['portfolio']['correlation']:.2f} with portfolio")

        return {
            "check": "risk_limits",
            "passed": len(issues) == 0,
            "issues": issues,
        }

    def _check_market_conditions(self, decision, context) -> dict:
        """시장 상황 적합성"""
        warnings = []

        # VIX 높을 때 공격적 매수
        if decision.decision == "buy" and context["macro"]["vix"] > 30:
            if decision.confidence > 7:
                warnings.append("High conviction buy during elevated VIX - ensure thesis is strong")

        # 하락장에서 레버리지/고변동성 종목
        if context["macro"]["sp500_trend"] == "bearish":
            if context["technical"]["volatility_20d"] > 40:
                warnings.append("Buying high-volatility stock in bearish market")

        return {
            "check": "market_conditions",
            "passed": True,  # Warning만, 실패는 아님
            "warning": "; ".join(warnings) if warnings else None,
        }
```

---

## Part 5: 리스크 관리 시스템

### 5.1 포지션 사이징

```python
class PositionSizer:
    """과학적 포지션 사이징"""

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        confidence: int,
        volatility: float,
        portfolio_value: float,
    ) -> PositionSize:
        """
        켈리 기준 + 변동성 조정 + 확신도 조정
        """
        # 1. 리스크 금액 계산
        risk_per_share = abs(entry_price - stop_loss_price)
        risk_pct = risk_per_share / entry_price

        # 2. 기본 리스크 예산 (거래당 1% 리스크)
        base_risk_budget = portfolio_value * 0.01

        # 3. 켈리 기준 계산 (과거 승률 기반)
        win_rate = self._get_historical_win_rate(symbol)
        avg_win = self._get_avg_win(symbol)
        avg_loss = self._get_avg_loss(symbol)

        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 최대 25%
        else:
            kelly_fraction = 0.02  # 데이터 없으면 보수적

        # 4. Half-Kelly 적용 (보수적)
        half_kelly = kelly_fraction / 2

        # 5. 변동성 조정 (고변동성 = 작은 포지션)
        volatility_factor = 0.20 / max(volatility, 0.10)  # 기준 변동성 20%
        volatility_factor = max(0.5, min(volatility_factor, 1.5))

        # 6. 확신도 조정
        confidence_factor = confidence / 10  # 1-10 → 0.1-1.0

        # 7. 최종 포지션 계산
        adjusted_risk_budget = base_risk_budget * volatility_factor * confidence_factor
        shares = int(adjusted_risk_budget / risk_per_share)

        # 8. 상한선 적용
        max_position_value = portfolio_value * 0.05  # 최대 5%
        max_shares_by_value = int(max_position_value / entry_price)

        max_shares_by_kelly = int(portfolio_value * half_kelly / entry_price)

        final_shares = min(shares, max_shares_by_value, max_shares_by_kelly)

        return PositionSize(
            shares=final_shares,
            value=final_shares * entry_price,
            weight=final_shares * entry_price / portfolio_value,
            risk_amount=final_shares * risk_per_share,
            risk_pct_of_portfolio=final_shares * risk_per_share / portfolio_value,
            method_details={
                "base_risk_budget": base_risk_budget,
                "kelly_fraction": kelly_fraction,
                "half_kelly": half_kelly,
                "volatility_factor": volatility_factor,
                "confidence_factor": confidence_factor,
            }
        )
```

### 5.2 드로다운 관리

```python
class DrawdownManager:
    """드로다운 관리 및 서킷 브레이커"""

    LIMITS = {
        "daily_loss": -0.02,       # 일일 -2%
        "weekly_loss": -0.05,      # 주간 -5%
        "monthly_loss": -0.10,     # 월간 -10%
        "max_drawdown": -0.15,     # 전체 -15%
    }

    ACTIONS = {
        "daily_loss": {
            "action": "PAUSE_NEW_BUYS",
            "duration": "end_of_day",
            "message": "일일 손실 한도 도달. 신규 매수 중단.",
        },
        "weekly_loss": {
            "action": "REDUCE_EXPOSURE_50",
            "duration": "end_of_week",
            "message": "주간 손실 한도 도달. 포지션 50% 축소.",
        },
        "monthly_loss": {
            "action": "DEFENSIVE_MODE",
            "duration": "end_of_month",
            "message": "월간 손실 한도 도달. 방어 모드 진입.",
        },
        "max_drawdown": {
            "action": "FULL_STOP",
            "duration": "manual_override",
            "message": "최대 낙폭 도달. 전체 거래 중단. 수동 검토 필요.",
        },
    }

    def check(self, portfolio_history: pd.DataFrame) -> DrawdownStatus:
        """드로다운 상태 체크"""
        current_value = portfolio_history["value"].iloc[-1]
        peak_value = portfolio_history["value"].max()

        # 각 기간별 손실 계산
        daily_return = self._calc_period_return(portfolio_history, days=1)
        weekly_return = self._calc_period_return(portfolio_history, days=5)
        monthly_return = self._calc_period_return(portfolio_history, days=21)
        max_drawdown = (current_value - peak_value) / peak_value

        # 한도 체크
        breaches = []
        if daily_return < self.LIMITS["daily_loss"]:
            breaches.append(("daily_loss", daily_return))
        if weekly_return < self.LIMITS["weekly_loss"]:
            breaches.append(("weekly_loss", weekly_return))
        if monthly_return < self.LIMITS["monthly_loss"]:
            breaches.append(("monthly_loss", monthly_return))
        if max_drawdown < self.LIMITS["max_drawdown"]:
            breaches.append(("max_drawdown", max_drawdown))

        # 가장 심각한 breach 기준 조치
        if breaches:
            worst = max(breaches, key=lambda x: abs(x[1]))
            action = self.ACTIONS[worst[0]]
            return DrawdownStatus(
                breached=True,
                breach_type=worst[0],
                breach_value=worst[1],
                action=action["action"],
                message=action["message"],
            )

        return DrawdownStatus(
            breached=False,
            current_drawdown=max_drawdown,
            daily_return=daily_return,
            weekly_return=weekly_return,
        )
```

### 5.3 서킷 브레이커

```python
class CircuitBreaker:
    """긴급 정지 시스템"""

    def __init__(self):
        self.triggers = {
            # 시장 레벨 트리거
            "vix_spike": {"threshold": 40, "action": "pause_all"},
            "sp500_daily_drop": {"threshold": -0.03, "action": "pause_buys"},
            "sp500_below_200sma": {"threshold": True, "action": "defensive"},

            # 포트폴리오 레벨 트리거
            "portfolio_daily_loss": {"threshold": -0.03, "action": "full_stop"},
            "single_stock_loss": {"threshold": -0.10, "action": "close_position"},

            # 시스템 레벨 트리거
            "api_error_rate": {"threshold": 0.10, "action": "pause_all"},
            "execution_slippage": {"threshold": 0.02, "action": "reduce_size"},
        }

        self.status = {
            "active": False,
            "trigger": None,
            "action": None,
            "timestamp": None,
        }

    def check_market_conditions(self, market_data: dict) -> CircuitBreakerStatus:
        """시장 조건 체크"""
        alerts = []

        # VIX 체크
        if market_data["vix"] > self.triggers["vix_spike"]["threshold"]:
            alerts.append({
                "trigger": "vix_spike",
                "value": market_data["vix"],
                "action": self.triggers["vix_spike"]["action"],
                "severity": "HIGH",
            })

        # S&P 500 일일 낙폭
        if market_data["sp500_daily_return"] < self.triggers["sp500_daily_drop"]["threshold"]:
            alerts.append({
                "trigger": "sp500_daily_drop",
                "value": market_data["sp500_daily_return"],
                "action": self.triggers["sp500_daily_drop"]["action"],
                "severity": "MEDIUM",
            })

        # S&P 500 200일선 하회
        if market_data["sp500_vs_200sma"] < 0:
            alerts.append({
                "trigger": "sp500_below_200sma",
                "value": market_data["sp500_vs_200sma"],
                "action": self.triggers["sp500_below_200sma"]["action"],
                "severity": "MEDIUM",
            })

        return CircuitBreakerStatus(
            triggered=len(alerts) > 0,
            alerts=alerts,
            recommended_action=self._get_most_severe_action(alerts),
        )

    def execute_action(self, action: str, portfolio: Portfolio):
        """조치 실행"""
        if action == "pause_all":
            portfolio.pause_all_trading()
            self._notify("🚨 전체 거래 중단")

        elif action == "pause_buys":
            portfolio.pause_buying()
            self._notify("⚠️ 신규 매수 중단")

        elif action == "defensive":
            portfolio.enter_defensive_mode()
            self._notify("🛡️ 방어 모드 진입")

        elif action == "full_stop":
            portfolio.emergency_stop()
            self._notify("🛑 긴급 정지 - 수동 검토 필요")

        elif action == "close_position":
            portfolio.close_losing_positions()
            self._notify("💔 손실 포지션 청산")
```

---

## Part 6: 백테스팅 및 검증

### 6.1 백테스팅 프레임워크

```python
class Backtester:
    """전략 백테스팅 엔진"""

    def __init__(self, strategy: Strategy, data: pd.DataFrame):
        self.strategy = strategy
        self.data = data
        self.results = None

    def run(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.001,    # 0.1%
    ) -> BacktestResult:
        """백테스트 실행"""

        portfolio = SimulatedPortfolio(initial_capital)
        trades = []

        for date in self.data.loc[start_date:end_date].index:
            # 전략 신호 생성
            signals = self.strategy.generate_signals(
                self.data.loc[:date]
            )

            for signal in signals:
                if signal.action == "buy":
                    trade = portfolio.buy(
                        symbol=signal.symbol,
                        price=signal.price * (1 + slippage),
                        shares=signal.shares,
                        commission=commission,
                    )
                elif signal.action == "sell":
                    trade = portfolio.sell(
                        symbol=signal.symbol,
                        price=signal.price * (1 - slippage),
                        shares=signal.shares,
                        commission=commission,
                    )

                if trade:
                    trades.append(trade)

            # 일일 포트폴리오 가치 기록
            portfolio.record_daily_value(date)

        # 결과 계산
        return self._calculate_results(portfolio, trades)

    def _calculate_results(self, portfolio, trades) -> BacktestResult:
        """성과 지표 계산"""
        equity_curve = portfolio.get_equity_curve()

        # 수익률 지표
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        cagr = self._calculate_cagr(equity_curve)

        # 리스크 지표
        daily_returns = equity_curve.pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252)
        sharpe = (cagr - 0.04) / volatility  # 무위험 수익률 4%
        sortino = self._calculate_sortino(daily_returns, cagr)
        max_drawdown = self._calculate_max_drawdown(equity_curve)

        # 거래 지표
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(sum(t.pnl for t in winning_trades) /
                          sum(t.pnl for t in losing_trades)) if losing_trades else 0

        return BacktestResult(
            total_return=total_return,
            cagr=cagr,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            equity_curve=equity_curve,
            trades=trades,
        )
```

### 6.2 워크포워드 분석

```python
class WalkForwardAnalyzer:
    """워크포워드 분석 (과적합 방지)"""

    def analyze(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        train_period: int = 252,  # 1년
        test_period: int = 63,    # 3개월
        num_folds: int = 8,
    ) -> WalkForwardResult:
        """
        롤링 윈도우로 학습/테스트 분리하여 과적합 검증
        """
        results = []

        for i in range(num_folds):
            train_start = i * test_period
            train_end = train_start + train_period
            test_start = train_end
            test_end = test_start + test_period

            if test_end > len(data):
                break

            # 학습 기간에서 파라미터 최적화
            train_data = data.iloc[train_start:train_end]
            optimized_params = strategy.optimize(train_data)

            # 테스트 기간에서 성과 측정
            test_data = data.iloc[test_start:test_end]
            strategy.set_params(optimized_params)
            test_result = Backtester(strategy, test_data).run()

            results.append({
                "fold": i + 1,
                "train_period": f"{data.index[train_start]} ~ {data.index[train_end]}",
                "test_period": f"{data.index[test_start]} ~ {data.index[test_end]}",
                "params": optimized_params,
                "test_return": test_result.total_return,
                "test_sharpe": test_result.sharpe_ratio,
                "test_max_dd": test_result.max_drawdown,
            })

        # 종합 분석
        avg_return = np.mean([r["test_return"] for r in results])
        avg_sharpe = np.mean([r["test_sharpe"] for r in results])
        consistency = len([r for r in results if r["test_return"] > 0]) / len(results)

        return WalkForwardResult(
            folds=results,
            avg_test_return=avg_return,
            avg_test_sharpe=avg_sharpe,
            consistency=consistency,  # 양수 수익 비율
            is_robust=avg_sharpe > 0.5 and consistency > 0.6,
        )
```

### 6.3 몬테카를로 시뮬레이션

```python
class MonteCarloSimulator:
    """미래 성과 시뮬레이션"""

    def simulate(
        self,
        historical_returns: pd.Series,
        initial_capital: float,
        years: int = 5,
        simulations: int = 10000,
    ) -> MonteCarloResult:
        """
        과거 수익률 분포 기반 미래 시뮬레이션
        """
        daily_returns = historical_returns
        mean_return = daily_returns.mean()
        std_return = daily_returns.std()

        trading_days = years * 252
        final_values = []

        for _ in range(simulations):
            # 랜덤 수익률 생성 (정규분포 가정)
            random_returns = np.random.normal(
                mean_return, std_return, trading_days
            )

            # 최종 자산 계산
            cumulative = np.cumprod(1 + random_returns)
            final_value = initial_capital * cumulative[-1]
            final_values.append(final_value)

        final_values = np.array(final_values)

        # 백분위 계산
        percentiles = {
            5: np.percentile(final_values, 5),
            25: np.percentile(final_values, 25),
            50: np.percentile(final_values, 50),
            75: np.percentile(final_values, 75),
            95: np.percentile(final_values, 95),
        }

        # 손실 확률
        loss_prob = np.mean(final_values < initial_capital)

        # 목표 달성 확률 (연 15% 복리)
        target = initial_capital * (1.15 ** years)
        target_prob = np.mean(final_values >= target)

        return MonteCarloResult(
            percentiles=percentiles,
            mean_final_value=np.mean(final_values),
            loss_probability=loss_prob,
            target_probability=target_prob,
            distribution=final_values,
        )
```

---

## Part 7: 개발 및 운영 로드맵

### 7.1 개발 단계

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         개발 로드맵 (16주)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [Phase 1: 기반 구축] 3주                                               │
│  ├─ Week 1: 프로젝트 구조, KIS API 연동                                │
│  ├─ Week 2: 데이터 수집 파이프라인 (시세, 재무, 뉴스)                  │
│  └─ Week 3: Supabase 스키마, 기본 CRUD                                 │
│                                                                         │
│  [Phase 2: 분석 엔진] 3주                                               │
│  ├─ Week 4: 기술적 분석 엔진 (지표, 패턴)                              │
│  ├─ Week 5: 기본적 분석 엔진 (밸류에이션, 퀄리티)                      │
│  └─ Week 6: 센티멘트 + 거시경제 분석 엔진                              │
│                                                                         │
│  [Phase 3: AI 시스템] 3주                                               │
│  ├─ Week 7: Claude 연동, 프롬프트 엔지니어링                           │
│  ├─ Week 8: 종합 점수 시스템, 의사결정 검증                            │
│  └─ Week 9: Reflection 엔진, 학습 루프                                 │
│                                                                         │
│  [Phase 4: 리스크 관리] 2주                                             │
│  ├─ Week 10: 포지션 사이징, 상관관계 관리                              │
│  └─ Week 11: 드로다운 관리, 서킷 브레이커                              │
│                                                                         │
│  [Phase 5: 백테스팅] 2주                                                │
│  ├─ Week 12: 백테스트 엔진, 성과 지표                                  │
│  └─ Week 13: 워크포워드, 몬테카를로                                    │
│                                                                         │
│  [Phase 6: 실행 & 모니터링] 2주                                         │
│  ├─ Week 14: 매매 실행, 주문 최적화                                    │
│  └─ Week 15: 대시보드, 알림 시스템                                     │
│                                                                         │
│  [Phase 7: 테스트 & 배포] 1주                                           │
│  └─ Week 16: Paper Trading, EC2 배포, 문서화                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 검증 단계 (필수)

```python
VALIDATION_STAGES = {
    "stage_1_backtest": {
        "duration": "2주",
        "description": "과거 5년 데이터 백테스트",
        "success_criteria": {
            "sharpe_ratio": "> 1.0",
            "max_drawdown": "< 15%",
            "win_rate": "> 55%",
            "walk_forward_consistency": "> 70%",
        },
        "action_if_fail": "전략 재설계",
    },

    "stage_2_paper_trading": {
        "duration": "4주",
        "description": "모의 투자 (KIS 모의투자 환경)",
        "success_criteria": {
            "live_vs_backtest_deviation": "< 20%",
            "execution_quality": "slippage < 0.2%",
            "system_uptime": "> 99%",
        },
        "action_if_fail": "시스템 최적화",
    },

    "stage_3_small_live": {
        "duration": "8주",
        "description": "소액 실전 투자 (총 자산의 10%)",
        "success_criteria": {
            "positive_return": True,
            "max_drawdown": "< 10%",
            "no_critical_errors": True,
        },
        "action_if_fail": "원인 분석 후 재시작 또는 전략 수정",
    },

    "stage_4_scaled_live": {
        "duration": "12주",
        "description": "확대 실전 투자 (총 자산의 30%)",
        "success_criteria": {
            "sharpe_ratio": "> 0.8",
            "beat_benchmark": "SPY 대비 양수",
        },
        "action_if_fail": "규모 축소 또는 전략 조정",
    },

    "stage_5_full_deployment": {
        "duration": "ongoing",
        "description": "전체 배정 자산 투자",
        "monitoring": "주간 성과 리뷰, 월간 전략 검토",
    },
}
```

### 7.3 운영 체크리스트

```markdown
## 일간 체크리스트
- [ ] 시스템 정상 작동 확인
- [ ] 전일 거래 리뷰
- [ ] 포트폴리오 손익 확인
- [ ] 주요 뉴스/이벤트 체크
- [ ] 알림 이상 여부 확인

## 주간 체크리스트
- [ ] 주간 성과 리포트 검토
- [ ] 리스크 지표 점검 (VaR, 드로다운)
- [ ] 섹터 배분 확인
- [ ] AI 결정 품질 분석
- [ ] 다음 주 주요 이벤트 캘린더 확인

## 월간 체크리스트
- [ ] 월간 성과 심층 분석
- [ ] 벤치마크 대비 성과
- [ ] 전략 파라미터 최적화 검토
- [ ] 비용 분석 (API, 수수료)
- [ ] 세금 관련 정리 (손익 실현)

## 분기 체크리스트
- [ ] 포트폴리오 리밸런싱
- [ ] 워크포워드 분석 업데이트
- [ ] AI 프롬프트 개선
- [ ] 새 데이터 소스 검토
- [ ] 시스템 업그레이드 계획
```

---

## Part 8: 비용 및 수익 예상

### 8.1 비용 구조

#### 필수 비용 (최소 운영)
| 항목 | 월간 비용 | 비고 |
|------|----------|------|
| AWS EC2 (t3.micro) | **$0-8** | 프리티어 1년 무료, 이후 ~$8 |
| Claude API (Sonnet) | **$15-30** | 일 10-20회 분석 기준 |
| Supabase | **$0** | Free tier (충분) |
| **필수 총합** | **$15-40/월** | **약 2-5만원** |

#### 데이터 소스 (전부 무료)
| 데이터 | 소스 | 비용 |
|--------|------|------|
| 실시간 시세/잔고 | KIS API (한국투자증권) | **무료** |
| 과거 시세/차트 | yfinance | **무료** |
| 재무제표/밸류에이션 | yfinance | **무료** |
| 뉴스/센티멘트 | Finnhub | **무료** (60회/분) |
| 애널리스트 평가/목표가 | Finnhub | **무료** |
| 경제 지표 (금리, CPI, 실업률 등) | FRED API | **무료** |
| 내부자 거래 | SEC EDGAR | **무료** |
| 공매도 데이터 | FINRA | **무료** |
| 기관 보유 (13F) | SEC EDGAR | **무료** |

#### 선택 비용 (필수 아님)
| 항목 | 월간 비용 | 비고 |
|------|----------|------|
| Financial Modeling Prep | $19 | 더 상세한 재무 데이터 (yfinance로 충분) |
| 커스텀 도메인 | ~$1 | 대시보드용 (선택) |

### 8.2 목표 수익률 시나리오

```python
SCENARIOS = {
    "conservative": {
        "cagr": 0.10,  # 연 10%
        "probability": 0.70,
        "5_year_multiple": 1.61,
    },
    "base_case": {
        "cagr": 0.15,  # 연 15%
        "probability": 0.50,
        "5_year_multiple": 2.01,
    },
    "optimistic": {
        "cagr": 0.20,  # 연 20%
        "probability": 0.25,
        "5_year_multiple": 2.49,
    },
}

# 예시: 초기 자본 $50,000
# Conservative: $50,000 → $80,500 (5년)
# Base Case: $50,000 → $100,500 (5년)
# Optimistic: $50,000 → $124,500 (5년)
```

### 8.3 손익분기점

```
월 운영비: ~$30 (약 4만원)
연 운영비: ~$360 (약 50만원)

손익분기 수익률 (자본 $50,000 기준):
- 연 0.7% ($350) → 운영비 커버
- 매우 낮은 허들!

목표 달성 시 순수익:
- 연 15% 수익 ($7,500) - 운영비 ($360) = $7,140 순수익
- 운영비 대비 ROI: 1,983%
```

---

## Part 9: 위험 고지 및 면책

### 9.1 투자 위험 고지

```
⚠️ 중요 고지사항

1. 이 시스템은 투자 조언이 아닙니다
2. 과거 성과가 미래 수익을 보장하지 않습니다
3. 원금 손실 위험이 있습니다
4. AI 판단이 항상 정확하지 않습니다
5. 시스템 오류로 인한 손실 가능성이 있습니다
6. 시장 상황에 따라 전략이 실패할 수 있습니다

투자 결정은 본인의 책임입니다.
전문 금융 자문가와 상담을 권장합니다.
```

### 9.2 시스템 제한사항

```
1. 미국 시장 정규 거래시간에만 주문 가능
2. 프리마켓/애프터마켓 거래 미지원 (KIS API 제한)
3. 환율 변동 위험 존재
4. API 장애 시 수동 개입 필요
5. 급격한 시장 변동 시 슬리피지 발생 가능
6. 연 250만원 초과 수익 시 양도세 22% 부과
```

---

*Document Version: 2.0*
*Last Updated: 2026-03-19*
*Author: JWCoin Wealth Builder System*