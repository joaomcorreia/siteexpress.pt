<?php
/*
Plugin Name: SiteExpress AI System
Description: Custom AI system integrated with OpenAI, with user dashboard and usage tracking.
Version: 1.0
Author: SiteExpress
*/

// Enqueue AI assistant scripts and styles
function siteexpress_ai_system_scripts() {
    wp_enqueue_script(
        'ai-system-js',
        plugin_dir_url( __FILE__ ) . 'ai-system.js',
        array(),
        '1.0',
        true
    );
    wp_enqueue_style(
        'ai-system-css',
        plugin_dir_url( __FILE__ ) . 'ai-system.css',
        array(),
        '1.0'
    );

    wp_localize_script(
        'ai-system-js',
        'siteexpressAiSystem',
        array(
            'restUrl' => rest_url( 'siteexpress/v1/ai-system' ),
        )
    );
}
add_action( 'wp_enqueue_scripts', 'siteexpress_ai_system_scripts' );

// Display AI Usage Dashboard for Users
function siteexpress_ai_usage_dashboard() {
    $user_id    = get_current_user_id();
    $usage_data = get_user_meta( $user_id, '_ai_usage_data', true );

    if ( ! is_array( $usage_data ) ) {
        $usage_data = array(
            'tokens_used'      => 0,
            'tokens_remaining' => 0,
            'plan'             => 'Not set',
        );
    }

    ob_start();
    ?>
    <div id="ai_usage_dashboard">
        <h1>Your AI Usage</h1>
        <p><strong>Usage this month:</strong> <?php echo esc_html( $usage_data['tokens_used'] ); ?> tokens</p>
        <p><strong>Remaining:</strong> <?php echo esc_html( $usage_data['tokens_remaining'] ); ?> tokens</p>
        <p><strong>Plan:</strong> <?php echo esc_html( $usage_data['plan'] ); ?></p>
        <button type="button" onclick="siteexpressAiSystemOpenChat()">Chat with Assistant</button>
        <div id="siteexpress_ai_system_chat" style="display:none;">
            <div id="siteexpress_ai_system_messages"></div>
            <input type="text" id="siteexpress_ai_system_input" placeholder="Ask me anything..." />
            <button type="button" onclick="siteexpressAiSystemSendMessage()">Send</button>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode( 'ai_usage_dashboard', 'siteexpress_ai_usage_dashboard' );

// REST API Endpoint to Handle AI Request from Frontend
function siteexpress_ai_system_endpoint() {
    register_rest_route(
        'siteexpress/v1',
        '/ai-system',
        array(
            'methods'             => 'POST',
            'callback'            => 'siteexpress_ai_system_callback',
            'permission_callback' => 'is_user_logged_in',
        )
    );
}
add_action( 'rest_api_init', 'siteexpress_ai_system_endpoint' );

// AI System Callback Function to Handle User's Requests
function siteexpress_ai_system_callback( WP_REST_Request $request ) {
    $user_message = sanitize_text_field( $request->get_param( 'message' ) );
    $user_id      = get_current_user_id();

    if ( empty( $user_message ) ) {
        return rest_ensure_response(
            array(
                'response' => 'Please enter a message first.',
            )
        );
    }

    $result = siteexpress_ai_system_get_openai_response( $user_message );

    if ( isset( $result['tokens_used'] ) && $user_id ) {
        siteexpress_track_ai_usage( $user_id, (int) $result['tokens_used'] );
    }

    return rest_ensure_response(
        array(
            'response' => $result['response'],
        )
    );
}

// Function to Call OpenAI API and Get Response
function siteexpress_ai_system_get_openai_response( $user_message ) {
    $user_id       = get_current_user_id();
    $business_data = get_user_meta( $user_id, '_business_data', true );
    $services      = get_user_meta( $user_id, '_services_data', true );

    if ( ! is_array( $business_data ) ) {
        $business_data = array();
    }

    if ( ! is_array( $services ) ) {
        $services = array();
    }

    if ( false !== stripos( $user_message, 'services' ) && ! empty( $services ) ) {
        $response = "Based on the information you provided, here are the services your business offers:\n";

        foreach ( $services as $service ) {
            $response .= '- ' . sanitize_text_field( $service ) . "\n";
        }

        return array(
            'response'    => trim( $response ),
            'tokens_used' => 0,
        );
    }

    if ( false !== stripos( $user_message, 'business' ) && ! empty( $business_data ) ) {
        $name    = isset( $business_data['name'] ) ? sanitize_text_field( $business_data['name'] ) : 'not available';
        $address = isset( $business_data['address'] ) ? sanitize_text_field( $business_data['address'] ) : 'not available';

        return array(
            'response'    => "Your business name is {$name}. The address is {$address}.",
            'tokens_used' => 0,
        );
    }

    $api_key = defined( 'SITEEXPRESS_OPENAI_API_KEY' ) ? SITEEXPRESS_OPENAI_API_KEY : '';

    if ( empty( $api_key ) ) {
        $api_key = $_ENV['OPENAI_API_KEY'] ?? $_SERVER['OPENAI_API_KEY'] ?? getenv( 'OPENAI_API_KEY' ) ?: '';
    }

    if ( empty( $api_key ) ) {
        $api_key = get_option( 'openai_api_key' );
    }

    if ( empty( $api_key ) ) {
        return array(
            'response'    => 'OpenAI API key is not configured.',
            'tokens_used' => 0,
        );
    }

    $openai_url = 'https://api.openai.com/v1/chat/completions';

    $args = array(
        'body'    => wp_json_encode(
            array(
                'model'       => 'gpt-4o-mini',
                'messages'    => array(
                    array(
                        'role'    => 'system',
                        'content' => 'You are the SiteExpress AI assistant. Reply concisely and helpfully.',
                    ),
                    array(
                        'role'    => 'user',
                        'content' => $user_message,
                    ),
                ),
                'max_tokens'  => 100,
                'temperature' => 0.7,
            )
        ),
        'headers' => array(
            'Content-Type'  => 'application/json',
            'Authorization' => 'Bearer ' . $api_key,
        ),
        'timeout' => 20,
    );

    $response = wp_remote_post( $openai_url, $args );
    if ( is_wp_error( $response ) ) {
        return array(
            'response'    => 'Sorry, I encountered an error.',
            'tokens_used' => 0,
        );
    }

    $status_code = wp_remote_retrieve_response_code( $response );
    $body        = wp_remote_retrieve_body( $response );
    $data        = json_decode( $body, true );

    if ( 200 !== $status_code || empty( $data['choices'][0]['message']['content'] ) ) {
        return array(
            'response'    => 'Sorry, I could not generate a response right now.',
            'tokens_used' => 0,
        );
    }

    return array(
        'response'    => sanitize_text_field( $data['choices'][0]['message']['content'] ),
        'tokens_used' => isset( $data['usage']['total_tokens'] ) ? (int) $data['usage']['total_tokens'] : 0,
    );
}

// Track User's AI Usage in the Dashboard
function siteexpress_track_ai_usage( $user_id, $tokens_used ) {
    $usage_data = get_user_meta( $user_id, '_ai_usage_data', true );

    if ( ! is_array( $usage_data ) ) {
        $usage_data = array(
            'tokens_used'      => 0,
            'tokens_remaining' => 0,
            'plan'             => 'Not set',
        );
    }

    $usage_data['tokens_used']      += $tokens_used;
    $usage_data['tokens_remaining'] -= $tokens_used;

    update_user_meta( $user_id, '_ai_usage_data', $usage_data );
}

// Add a simple plan-based token limit system.
function siteexpress_set_token_limit( $user_id, $plan ) {
    $usage_data = get_user_meta( $user_id, '_ai_usage_data', true );

    if ( ! is_array( $usage_data ) ) {
        $usage_data = array(
            'tokens_used'      => 0,
            'tokens_remaining' => 0,
            'tokens_limit'     => 0,
            'plan'             => $plan,
        );
    }

    if ( 'starter' === $plan ) {
        $usage_data['tokens_limit']     = 1000;
        $usage_data['tokens_remaining'] = 1000;
    } elseif ( 'premium' === $plan ) {
        $usage_data['tokens_limit']     = 5000;
        $usage_data['tokens_remaining'] = 5000;
    }

    $usage_data['plan'] = $plan;

    update_user_meta( $user_id, '_ai_usage_data', $usage_data );
}
