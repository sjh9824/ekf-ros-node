from setuptools import setup

package_name = 'ekf_ros_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'numpy'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='EKF-based GNSS+IMU odometry publisher/subscriber demo over ROS2 topics',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ekf_publisher_node = ekf_ros_pkg.ekf_publisher_node:main',
            'trajectory_subscriber_node = ekf_ros_pkg.trajectory_subscriber_node:main',
        ],
    },
)
