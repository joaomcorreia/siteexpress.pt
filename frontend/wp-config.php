<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the website, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/
 *
 * @package WordPress
 */

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'siteexpress' );

/** Database username */
define( 'DB_USER', 'root' );

/** Database password */
define( 'DB_PASSWORD', '' );

/** Database hostname */
define( 'DB_HOST', 'localhost' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8mb4' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY',         'loC6(c;fJCus+d4@:<h9izjl2Re01<@V.,Yp^`@Du&@Eu<%%t%hD!T^iNQ$uWqWJ' );
define( 'SECURE_AUTH_KEY',  '%@]o;WD7<v!1^X7}uQbL2^X5^.Aj!I k61#mlo]|^_Q!$u=2{wl2!;-F|.kfcbpJ' );
define( 'LOGGED_IN_KEY',    '[p$*_pCj)s!;+*Sfx ,7$^[EP+_vi:A7*?>JQoZwil8.$|s7&xx*Sw3RxXL|Un!D' );
define( 'NONCE_KEY',        '0n(Og)O?ty9mdzf3^#~UL440#7w_*7[53mSkieIwpGq|i%^4if)-=Al3e<sc`0+?' );
define( 'AUTH_SALT',        'b8vRIdq{8{@J>xHtO^Jz$ Z=E1U/hUoe4A>W(4,+[&4pnZh(*G>hU s;4WB cP|M' );
define( 'SECURE_AUTH_SALT', 'hqL6*yE96; t0*>JZdgCX0h>;SITn.Tl|`<Cs R;n0PlrV=` RU2!BM{,2Ux694&' );
define( 'LOGGED_IN_SALT',   'Rw88G9;<087FexL-fCi nFp:P(d-u$ek8Sp?X37iL(R(M$JM;sv*@ eUAdYzrUN4' );
define( 'NONCE_SALT',       '/9B]1F}H#!!Gu(1G^~(UGEOp)XC4i*8?5oNwxg2{R&aq<8K.T>JvIxue_x+?Jvs1' );

/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 *
 * At the installation time, database tables are created with the specified prefix.
 * Changing this value after WordPress is installed will make your site think
 * it has not been installed.
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/#table-prefix
 */
$table_prefix = 'wp_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/
 */
define( 'WP_DEBUG', false );

/* Add any custom values between this line and the "stop editing" line. */

require_once __DIR__ . '/vendor/autoload.php';

$dotenv = Dotenv\Dotenv::createImmutable( __DIR__ );
$dotenv->load();

if ( ! defined( 'SITEEXPRESS_OPENAI_API_KEY' ) ) {
	define(
		'SITEEXPRESS_OPENAI_API_KEY',
		$_ENV['OPENAI_API_KEY'] ?? $_SERVER['OPENAI_API_KEY'] ?? getenv( 'OPENAI_API_KEY' ) ?: ''
	);
}


/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
