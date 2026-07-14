"""
Trajectory Subscriber Node.

Subscribes to `/ekf_odom` (nav_msgs/Odometry), logs each received pose,
and accumulates the trajectory. On shutdown (Ctrl+C, or when the
publisher finishes and calls rclpy.shutdown()), saves a plot of the
full received trajectory - proving the data actually made it across
the ROS2 pub/sub boundary between two independent processes.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class TrajectorySubscriberNode(Node):
    def __init__(self):
        super().__init__('trajectory_subscriber_node')

        self.declare_parameter('output_path', 'ekf_ros_trajectory.png')

        self.subscription = self.create_subscription(
            Odometry, 'ekf_odom', self.listener_callback, 10,
        )
        self.positions = []
        self.get_logger().info('Trajectory subscriber started, listening on /ekf_odom')

    def listener_callback(self, msg):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        self.positions.append((x, y))
        self.get_logger().info(f'[{len(self.positions):04d}] x={x:.2f}  y={y:.2f}')

    def save_plot(self):
        if not self.positions:
            self.get_logger().warn('No odometry messages received - nothing to plot.')
            return

        import numpy as np
        import matplotlib
        matplotlib.use('Agg')  # headless-safe backend
        import matplotlib.pyplot as plt

        arr = np.array(self.positions)
        out_path = self.get_parameter('output_path').value

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(arr[:, 0], arr[:, 1], color='tab:blue', linewidth=2)
        ax.scatter(arr[0, 0], arr[0, 1], color='green', s=80, label='start', zorder=3)
        ax.scatter(arr[-1, 0], arr[-1, 1], color='red', s=80, label='end', zorder=3)
        ax.set_xlabel('x (m)')
        ax.set_ylabel('y (m)')
        ax.set_title(f'EKF trajectory received via ROS2 topic ({len(arr)} messages)')
        ax.set_aspect('equal')
        ax.legend()
        ax.grid(alpha=0.3)
        fig.savefig(out_path, dpi=150, bbox_inches='tight')

        self.get_logger().info(f'Saved received trajectory plot -> {out_path}')


def main(args=None):
    rclpy.init(args=args)
    node = TrajectorySubscriberNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.save_plot()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
