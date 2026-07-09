<?php
/*
Plugin Name: SiteExpress Custom Plugin
Description: A custom plugin for SiteExpress.pt, integrating AI assistant, subdomain creation, and website generation.
Version: 1.0
Author: SiteExpress
*/

// Enqueue necessary scripts and styles
function siteexpress_enqueue_scripts() {
    wp_enqueue_script(
        'ai-assistant-js',
        plugin_dir_url( __FILE__ ) . 'ai-assistant.js',
        array(),
        '1.0',
        true
    );
    wp_enqueue_style(
        'ai-assistant-css',
        plugin_dir_url( __FILE__ ) . 'ai-assistant.css',
        array(),
        '1.0'
    );

    wp_localize_script(
        'ai-assistant-js',
        'siteexpressAiAssistant',
        array(
            'restUrl' => rest_url( 'siteexpress/v1/ai-assistant' ),
        )
    );
}
add_action( 'wp_enqueue_scripts', 'siteexpress_enqueue_scripts' );

// Add AI Assistant Button in Footer (Floating Chat)
function siteexpress_ai_assistant() {
    ?>
    <div id="ai_assistant">
        <button type="button" onclick="openChat()">Chat with Assistant</button>
        <div id="chat_box" style="display:none;">
            <div id="chat_header">
                <h3>AI Assistant</h3>
                <button type="button" onclick="closeChat()">Close</button>
            </div>
            <div id="chat_content"></div>
            <input type="text" id="user_input" placeholder="Ask me anything..." />
            <button type="button" onclick="sendMessage()">Send</button>
        </div>
    </div>
    <?php
}
add_action( 'wp_footer', 'siteexpress_ai_assistant' );

// REST API Endpoint for AI Assistant Interaction
function siteexpress_ai_assistant_endpoint() {
    register_rest_route(
        'siteexpress/v1',
        '/ai-assistant',
        array(
            'methods'             => 'POST',
            'callback'            => 'siteexpress_ai_assistant_callback',
            'permission_callback' => '__return_true',
        )
    );
}
add_action( 'rest_api_init', 'siteexpress_ai_assistant_endpoint' );

// Callback for AI Assistant to Process Messages and Return AI Response
function siteexpress_ai_assistant_callback( WP_REST_Request $request ) {
    $user_message = sanitize_text_field( $request->get_param( 'message' ) );

    if ( empty( $user_message ) ) {
        return rest_ensure_response(
            array(
                'response' => 'Please enter a message first.',
            )
        );
    }

    $openai_response = siteexpress_get_openai_response( $user_message );

    return rest_ensure_response(
        array(
            'response' => $openai_response,
        )
    );
}

// Function to Call OpenAI API for Responses
function siteexpress_get_openai_response( $user_message ) {
    $api_key = defined( 'SITEEXPRESS_OPENAI_API_KEY' ) ? SITEEXPRESS_OPENAI_API_KEY : '';

    if ( empty( $api_key ) ) {
        $api_key = $_ENV['OPENAI_API_KEY'] ?? $_SERVER['OPENAI_API_KEY'] ?? getenv( 'OPENAI_API_KEY' ) ?: '';
    }

    if ( empty( $api_key ) ) {
        $api_key = get_option( 'openai_api_key' );
    }

    if ( empty( $api_key ) ) {
        return 'OpenAI API key is not configured.';
    }

    $openai_url = 'https://api.openai.com/v1/chat/completions';

    $args = array(
        'body'    => wp_json_encode(
            array(
                'model'       => 'gpt-4o-mini',
                'messages'    => array(
                    array(
                        'role'    => 'system',
                        'content' => 'You are a concise assistant for SiteExpress.pt users.',
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
        return 'Sorry, I encountered an error.';
    }

    $status_code = wp_remote_retrieve_response_code( $response );
    $body        = wp_remote_retrieve_body( $response );
    $data        = json_decode( $body, true );

    if ( 200 !== $status_code || empty( $data['choices'][0]['message']['content'] ) ) {
        return 'Sorry, I could not generate a response right now.';
    }

    return sanitize_text_field( $data['choices'][0]['message']['content'] );
}

// Subdomain Creation and Site Generation (using CyberPanel API or CLI)
function siteexpress_create_subdomain_and_site( $business_name ) {
    $subdomain = sanitize_title_with_dashes( $business_name );

    // Call CyberPanel API to create the subdomain and site
    $cyberpanel_url     = 'http://your-cyberpanel-api-url';
    $cyberpanel_api_key = 'your-cyberpanel-api-key';

    $args = array(
        'body'    => wp_json_encode(
            array(
                'subdomain' => $subdomain,
                'domain'    => 'siteexpress.pt',
                'api_key'   => $cyberpanel_api_key,
            )
        ),
        'headers' => array(
            'Content-Type' => 'application/json',
        ),
        'timeout' => 20,
    );

    $response = wp_remote_post( $cyberpanel_url, $args );
    if ( is_wp_error( $response ) ) {
        return 'Error creating subdomain';
    }

    // Site creation logic could be added here (copy templates, set up site structure)
    return 'Subdomain created successfully!';
}
