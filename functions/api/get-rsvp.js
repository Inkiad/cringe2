// Get all RSVP submissions
export async function onRequestGet(context) {
  try {
    const { env } = context;
    
    // List all keys starting with "rsvp:"
    const list = await env.RSVP_STORAGE.list({ prefix: 'rsvp:' });
    
    // Fetch all RSVPs
    const rsvps = [];
    for (const key of list.keys) {
      const value = await env.RSVP_STORAGE.get(key.name);
      if (value) {
        rsvps.push(JSON.parse(value));
      }
    }
    
    // Sort by timestamp (newest first)
    rsvps.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    return new Response(JSON.stringify({ 
      success: true,
      rsvps: rsvps,
      count: rsvps.length
    }), {
      status: 200,
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
    
  } catch (error) {
    console.error('Error fetching RSVPs:', error);
    return new Response(JSON.stringify({ 
      success: false, 
      error: 'Failed to fetch RSVPs' 
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
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    }
  });
}
