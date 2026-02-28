<?php
/**
 * 在 WordPress 容器内运行，为用户 1（管理员）创建应用程序密码。
 * 用法: docker exec wp_a php /tmp/wp_create_app_password.php
 * 输出: 仅一行明文密码（供荣耀AI系统使用）
 */
define( 'WP_USE_THEMES', false );
require_once '/var/www/html/wp-load.php';

$user_id = isset( $argv[1] ) ? (int) $argv[1] : 1;
$name    = isset( $argv[2] ) ? $argv[2] : 'GloryAI';

if ( ! class_exists( 'WP_Application_Passwords' ) ) {
    fwrite( STDERR, "WordPress 5.6+ required (WP_Application_Passwords not found)\n" );
    exit( 1 );
}

$result = WP_Application_Passwords::create_new_application_password( $user_id, array( 'name' => $name ) );

if ( is_wp_error( $result ) ) {
    fwrite( STDERR, $result->get_error_message() . "\n" );
    exit( 1 );
}

echo $result[0];
exit( 0 );
