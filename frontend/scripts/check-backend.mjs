const base = (process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
const parsed = new URL(base);
const origin = parsed.origin;
const schemaUrl = `${origin}/openapi.json`;

console.log(`Checking FastAPI OpenAPI endpoint: ${schemaUrl}`);
try {
  const response = await fetch(schemaUrl, { signal: AbortSignal.timeout(7000) });
  if (!response.ok) {
    console.error(`Backend responded with HTTP ${response.status} at ${schemaUrl}`);
    process.exit(1);
  }
  const schema = await response.json();
  const paths = Object.keys(schema.paths || {});
  const apiPrefix = parsed.pathname.replace(/\/$/, '');
  const required = [
    ['GET', `${apiPrefix}/conversations`],
    ['POST', `${apiPrefix}/conversations`],
    ['POST', `${apiPrefix}/conversations/{conversation_id}/messages`],
    ['POST', `${apiPrefix}/auth/login`],
    ['POST', `${apiPrefix}/auth/signup`],
  ];
  console.log(`Connected: ${schema.info?.title || 'FastAPI application'} ${schema.info?.version || ''}`.trim());
  console.log(`Found ${paths.length} registered OpenAPI paths.`);
  for (const [method, expectedPath] of required) {
    const normalized = expectedPath.replace(/\{[^}]+\}/g, (part) => part);
    const found = paths.find((path) => path === normalized);
    const hasMethod = found && schema.paths[found]?.[method.toLowerCase()];
    console.log(`${hasMethod ? 'OK ' : 'CHECK'} ${method} ${expectedPath}${hasMethod ? '' : ' (not found; adjust frontend routes to match your backend)'}`);
  }
  console.log('\nThis checks reachability and route names, not authentication, database writes, or agent execution.');
} catch (error) {
  console.error(`Could not reach backend OpenAPI at ${schemaUrl}. Start FastAPI and check the URL/CORS configuration.`);
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
