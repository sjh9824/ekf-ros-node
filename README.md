# EKF 위치추정 결과를 ROS2 노드로 Publish/Subscribe

`gnss-imu-ekf-localization`에서 만든 EKF를 ROS2 노드 안에 넣어, **Publisher(위치추정) → 토픽 → Subscriber(구독/시각화)** 구조로 분리한 프로젝트입니다. ROS의 핵심인 노드-토픽 기반 발행-구독(pub/sub) 통신 구조를 실습 수준에서 경험하는 것이 목적입니다.

> ⚠️ **실행 환경 안내**: 이 프로젝트는 ROS2(rclpy)가 설치된 환경에서만 실행할 수 있습니다. 코드는 ROS2 Humble 기준 ament_python 패키지 규격에 맞춰 작성했지만, 이 문서를 작성한 환경에는 ROS2가 설치되어 있지 않아 **문법 검증(`python3 -m py_compile`)까지만 확인**했고, 실제 `colcon build` / `ros2 run` 실행 검증은 아직 못 했습니다. 본인 환경에서 빌드 후 아래 "실행 결과" 섹션을 실제 캡처로 교체해주세요.

## 진행 상태

- [x] EKF 로직 (기존 프로젝트 재사용)
- [x] Publisher 노드 작성 (`nav_msgs/Odometry` 발행)
- [x] Subscriber 노드 작성 (구독 + 궤적 시각화)
- [x] ament_python 패키지 구조 (`package.xml`, `setup.py`)
- [x] 문법 검증 (`py_compile`)
- [ ] 실제 ROS2 환경에서 빌드 및 실행 검증
- [ ] `ros2 topic echo` / `rviz2` 캡처

## 배경 지식

ROS는 여러 프로세스(노드)가 하나의 프로그램이 아니라 **독립된 프로세스로 실행되며, 토픽(topic)을 통해 메시지를 주고받는 발행-구독 구조**로 동작합니다.

- 이 프로젝트에서는 `ekf_publisher_node`가 위치추정 결과를, `nav_msgs/Odometry` 메시지 타입으로 `/ekf_odom` 토픽에 발행(publish)
- `trajectory_subscriber_node`는 이 토픽을 구독(subscribe)해서 로그를 출력하고, 누적된 궤적을 이미지로 저장
- 두 노드는 서로의 존재를 몰라도 되고(loose coupling), 토픽 이름과 메시지 타입만 맞으면 통신이 성립함 — 예를 들어 나중에 rviz2나 다른 시각화 노드를 추가로 붙여도 publisher 코드는 전혀 건드릴 필요가 없음

`nav_msgs/Odometry`를 선택한 이유는 위치(`pose.pose.position`), 자세(`pose.pose.orientation`, 쿼터니언), 속도(`twist.twist`)를 표준화된 하나의 메시지로 표현하기 때문입니다 — 자율주행 스택에서 위치추정 모듈의 출력으로 가장 널리 쓰이는 메시지 타입입니다.

## 노드/토픽 구조

```
┌───────────────────────┐         /ekf_odom          ┌──────────────────────────────┐
│   ekf_publisher_node   │  (nav_msgs/Odometry, 10Hz)  │  trajectory_subscriber_node   │
│                        │ ───────────────────────────▶ │                              │
│  - 합성 IMU/GNSS 생성   │                              │  - 메시지 로그 출력            │
│  - EKF predict/update  │                              │  - 궤적 누적 후 이미지 저장     │
└───────────────────────┘                              └──────────────────────────────┘
```

## 프로젝트 구조

ROS2 컨벤션에 맞춰 `src/` 아래에 패키지를 두는 workspace 구조입니다.

```
ekf-ros-node/
└── src/
    └── ekf_ros_pkg/                        # ament_python 패키지
        ├── package.xml
        ├── setup.py
        ├── setup.cfg
        ├── resource/
        │   └── ekf_ros_pkg                 # ament 리소스 마커 (빈 파일)
        └── ekf_ros_pkg/                     # 실제 파이썬 모듈
            ├── __init__.py
            ├── ekf.py                        # gnss-imu-ekf-localization 재사용
            ├── sensor_sim.py                 # gnss-imu-ekf-localization 재사용
            ├── ekf_publisher_node.py
            └── trajectory_subscriber_node.py
```

## 환경 셋업 (가장 시간이 걸리는 부분)

- Ubuntu 22.04 (또는 WSL2 + Ubuntu 22.04) + **ROS2 Humble** 권장
- 설치는 [ROS2 공식 문서](https://docs.ros.org/en/humble/Installation.html)의 `apt` 설치 가이드를 따라주세요 (본 README 범위 밖)
- 설치 확인:
  ```bash
  source /opt/ros/humble/setup.bash
  ros2 --version
  ```

## 빌드 및 실행 방법

```bash
# 1. 워크스페이스 클론 및 빌드
git clone https://github.com/<username>/ekf-ros-node.git
cd ekf-ros-node
source /opt/ros/humble/setup.bash
colcon build --packages-select ekf_ros_pkg
source install/setup.bash

# 2. Publisher 노드 실행 (터미널 1)
ros2 run ekf_ros_pkg ekf_publisher_node

# 3. Subscriber 노드 실행 (터미널 2, 같은 워크스페이스 source 필요)
ros2 run ekf_ros_pkg trajectory_subscriber_node
```

파라미터를 바꾸고 싶다면:
```bash
ros2 run ekf_ros_pkg ekf_publisher_node --ros-args -p publish_rate_hz:=20.0 -p gnss_std:=2.0
ros2 run ekf_ros_pkg trajectory_subscriber_node --ros-args -p output_path:=my_trajectory.png
```

## 검증 방법

```bash
# 토픽이 정상적으로 발행되는지 확인
ros2 topic list
# /ekf_odom 이 보여야 함

# 메시지 내용 확인
ros2 topic echo /ekf_odom

# 발행 주기(Hz) 확인
ros2 topic hz /ekf_odom
```

선택 사항: `rviz2`를 켜고 `Odometry` 디스플레이를 `/ekf_odom` 토픽으로 추가하면 실시간으로 궤적이 그려지는 것을 시각적으로 확인할 수 있습니다.

## 실행 결과

> 아래는 본인 환경에서 실행 후 채워 넣을 자리입니다.

```
[ros2 topic echo /ekf_odom 결과 캡처 삽입 위치]
```

```
[trajectory_subscriber_node가 저장한 ekf_ros_trajectory.png 삽입 위치]
```

- 발행 주기(Hz): `[ros2 topic hz 결과 입력]`
- 총 수신 메시지 수: `[trajectory_subscriber_node 로그의 마지막 인덱스 입력]`

## 배운 점 (작성 가이드 — 실제로 실행해보고 본인 언어로 재작성 권장)

- ROS 노드가 왜 하나의 프로세스가 아니라 여러 노드의 분산 구조로 설계되는지: publisher가 죽어도 subscriber는 독립적으로 계속 실행되고, 반대로 subscriber를 나중에 추가로 붙여도 publisher 코드를 전혀 건드릴 필요가 없다는 느슨한 결합(loose coupling)을 체감
- 메시지 타입(`nav_msgs/Odometry`)이 정해져 있기 때문에, 이 프로젝트의 EKF publisher와 전혀 다른 팀이 만든 rviz2/rqt 같은 범용 도구가 별도 설정 없이 바로 호환된다는 점
- (실행 후 추가) 발행 주기(`publish_rate_hz`)와 실제 `ros2 topic hz` 측정값의 차이, 있었다면 그 원인

## 한계 및 개선 방향

- 현재 IMU/GNSS 입력이 실제 센서가 아니라 노드 시작 시 미리 생성한 합성 데이터(`sensor_sim.py`) — 실제로는 `sensor_msgs/Imu`, `sensor_msgs/NavSatFix`를 구독하는 별도의 센서 드라이버 노드로 교체하면 완전한 "라이브" 파이프라인이 됨
- 서비스(service)가 아니라 토픽(topic)을 쓴 이유: 위치추정처럼 **지속적으로 갱신되는 스트림 데이터**는 요청-응답 방식인 서비스보다, 발행 즉시 다수의 구독자에게 전달되는 토픽이 적합하기 때문. 반대로 "현재 위치를 한 번만 알려줘" 같은 단발성 요청이라면 서비스가 더 적합할 수 있음
- 두 노드가 프로세스로는 분리되어 있지만 여전히 같은 머신에서 실행됨 — 진짜 분산 시스템(여러 대의 컴퓨터)에서의 통신 지연/QoS 설정 등은 다루지 않음
- QoS(Quality of Service) 설정을 기본값(depth=10)으로만 사용 — 실제로는 위치추정처럼 최신 값이 중요한 데이터는 `BEST_EFFORT` + 작은 큐 depth가 더 적합할 수 있음

## 참고 자료

- [ROS2 Humble 공식 문서](https://docs.ros.org/en/humble/index.html)
- [nav_msgs/Odometry 메시지 정의](https://docs.ros2.org/humble/api/nav_msgs/msg/Odometry.html)
- [ROS2 rclpy Publisher/Subscriber 튜토리얼](https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
