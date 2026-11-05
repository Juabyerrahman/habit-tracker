async function proxy(context) {
  const incomingUrl = new URL(context.request.url);

  const backendUrl = new URL(
    incomingUrl.pathname + incomingUrl.search,
    "https://habit-tracker-api-u7f0.onrender.com"
  );

  const upstreamRequest = new Request(backendUrl, context.request);

  return fetch(upstreamRequest, {
    redirect: "manual"
  });
}

export const onRequest = proxy;