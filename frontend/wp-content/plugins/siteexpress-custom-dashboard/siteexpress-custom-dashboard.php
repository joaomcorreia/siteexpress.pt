<?php
/*
Plugin Name: SiteExpress Custom Dashboard
Description: Custom plugin for managing the SiteExpress dashboard and restricting WordPress admin access for users.
Version: 1.0
Author: SiteExpress
*/

// Restrict WordPress Admin Access for Users
function siteexpress_restrict_admin() {
    $user = wp_get_current_user();

    $allowed_pages = array(
        'profile.php',
        'admin-ajax.php',
    );

    if ( ! current_user_can( 'administrator' ) ) {
        $current_page = basename( $_SERVER['PHP_SELF'] );
        if ( ! in_array( $current_page, $allowed_pages, true ) ) {
            wp_redirect( home_url( '/siteexpress-dashboard' ) ); // Redirect to custom dashboard
            exit;
        }
    }
}
add_action( 'admin_init', 'siteexpress_restrict_admin' );

// Add SiteExpress Dashboard Menu Item
function siteexpress_dashboard_menu() {
    add_menu_page(
        'SiteExpress Dashboard',      // Page Title
        'SiteExpress',                // Menu Title
        'manage_options',             // Required Capability
        'siteexpress-dashboard',      // Menu Slug
        'siteexpress_dashboard_page', // Function to display the page
        'dashicons-dashboard',        // Icon
        3                              // Position in the menu
    );
}
add_action( 'admin_menu', 'siteexpress_dashboard_menu' );

// Display Custom Dashboard Content
function siteexpress_dashboard_page() {
    echo '<h1>Welcome to SiteExpress Dashboard</h1>';
    // Custom content here, e.g., AI data management, site settings, etc.
    echo '<p>Manage your business information and AI-generated content.</p>';
}

// Add Shortcode for Frontend Dashboard Access
function siteexpress_dashboard_shortcode() {
    ob_start();
    ?>
    <h1>Welcome to Your SiteExpress Dashboard</h1>
    <p>Here you can manage your website's details, AI-generated content, and more!</p>
    <!-- Add more functionality as needed -->
    <?php
    return ob_get_clean();
}
add_shortcode( 'siteexpress_dashboard', 'siteexpress_dashboard_shortcode' );
