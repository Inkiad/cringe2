// Handle RSVP form submissions
export async function onRequestPost(context) {
  try {
    const { request, env } = context;
    
    // Get form data
    const formData = await request.json();
    
    // Validate required fields - updated to accept 'dates' array
    if (!formData.name || (!formData.dates && !formData.date) || !formData.format) {
      return new Response(JSON.stringify({ 
        success: false, 
        error: 'Missing required fields' 
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Create storage key with timestamp and name
    const timestamp = Date.now();
    const sanitizedName = formData.name.replace(/[^a-zA-Z0-9]/g, '_');
    const key = `rsvp:${timestamp}:${sanitizedName}`;
    
    // Store in KV
    await env.RSVP_STORAGE.put(key, JSON.stringify(formData));
    
    return new Response(JSON.stringify({ 
      success: true,
      message: 'RSVP submitted successfully!' 
    }), {
      status: 200,
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
    
  } catch (error) {
    console.error('Error storing RSVP:', error);
    return new Response(JSON.stringify({ 
      success: false, 
      error: 'Failed to submit RSVP' 
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Handle CORS preflight
export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    }
  });
}
