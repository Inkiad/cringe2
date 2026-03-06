export async function onRequest() {
    const resp = await fetch('https://letterboxd.com/inkyyy/rss/');
    const xml = await resp.text();
    const match = xml.match(/<letterboxd:filmTitle>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/letterboxd:filmTitle>/);
    const title = match ? match[1] : null;
    return new Response(JSON.stringify({ title }), {
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'public, max-age=300',
        },
    });
}
