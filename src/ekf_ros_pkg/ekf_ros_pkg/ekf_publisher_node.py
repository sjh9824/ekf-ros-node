"""
EKF Publisher Node.

Runs the same GNSS+IMU EKF fusion used in `gnss-imu-ekf-localization`,
but instead of writing results to a file, it publishes the estimated
pose/velocity as a `nav_msgs/Odometry` message on the `/ekf_odom` topic
at a fixed rate, one EKF predict+update step per timer tick.

This demonstrates how a localization module would sit inside a larger
ROS2-based autonomous driving stack: other nodes (planners, controllers,
visualizers) subscribe to /ekf_odom without needing to know anything
about how the estimate was produced.
"""

import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

from ekf_ros_pkg.ekf import EKF
from ekf_ros_pkg.sensor_sim import generate_synthetic_trajectory, add_gnss_noise


def yaw_to_quaternion(yaw):
    """2D yaw-only rotation -> quaternion (roll=pitch=0)."""
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class EKFPublisherNode(Node):
    def __init__(self):
        super().__init__('ekf_publisher_node')

        self.declare_parameter('publish_rate_hz', 10.0)
        self.declare_parameter('gnss_std', 3.0)
        rate_hz = self.get_parameter('publish_rate_hz').value
        gnss_std = self.get_parameter('gnss_std').value

        self.publisher_ = self.create_publisher(Odometry, 'ekf_odom', 10)

        # Pre-generate one synthetic drive (ground truth + noisy IMU) for this run.
        # Swap this out for a real IMU/GNSS driver node publishing sensor_msgs/Imu
        # and sensor_msgs/NavSatFix to make this a fully "live" pipeline.
        self.data = generate_synthetic_trajectory()
        self.gnss_x, self.gnss_y = add_gnss_noise(self.data['x'], self.data['y'], std=gnss_std)

        self.ekf = EKF(x0=[
            self.data['x'][0], self.data['y'][0],
            self.data['yaw'][0], self.data['vf'][0],
        ])

        self.index = 0
        self.n_steps = len(self.data['af'])

        timer_period = 1.0 / rate_hz
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            f'EKF publisher started: publishing /ekf_odom at {rate_hz} Hz '
            f'({self.n_steps} steps total, simulated GNSS std={gnss_std} m)'
        )

    def timer_callback(self):
        if self.index >= self.n_steps - 1:
            self.get_logger().info('Reached end of trajectory. Shutting down.')
            self.timer.cancel()
            rclpy.shutdown()
            return

        i = self.index
        dt = self.data['dt'][i]

        # Prediction step (IMU) + update step (GNSS) - identical logic to the
        # standalone gnss-imu-ekf-localization project.
        self.ekf.predict(u=[self.data['af'][i], self.data['wu'][i]], dt=dt)
        self.ekf.update(z=[self.gnss_x[i + 1], self.gnss_y[i + 1]])

        x, y, yaw, v = self.ekf.x
        qx, qy, qz, qw = yaw_to_quaternion(yaw)

        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.child_frame_id = 'base_link'

        msg.pose.pose.position.x = float(x)
        msg.pose.pose.position.y = float(y)
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        msg.twist.twist.linear.x = float(v)
        msg.twist.twist.angular.z = float(self.data['wu'][i])

        # Populate the diagonal of the 6x6 pose covariance from the EKF's P matrix
        # (x, y, yaw only - roll/pitch/z are not modeled by this 2D filter).
        cov = [0.0] * 36
        cov[0 * 6 + 0] = float(self.ekf.P[0, 0])   # x-x
        cov[1 * 6 + 1] = float(self.ekf.P[1, 1])   # y-y
        cov[5 * 6 + 5] = float(self.ekf.P[2, 2])   # yaw-yaw
        msg.pose.covariance = cov

        self.publisher_.publish(msg)
        self.get_logger().debug(f'Published: x={x:.2f} y={y:.2f} yaw={yaw:.2f} v={v:.2f}')

        self.index += 1


def main(args=None):
    rclpy.init(args=args)
    node = EKFPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
