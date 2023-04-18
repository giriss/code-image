## What it does?
You can send a piece of code to this API and we'll convert it to a nice shareable image or html code that you can embed.

## How to use?

### Send a request with the code snippet to `/highlight`

```http
POST /highlight HTTP/1.1
Content-Type: application/json
Host: code2image.up.railway.app
Content-Length: 122

{
  "code": "function main(_args) {\n  console.log('hello world');\n}",
  "language": "javascript",
  "filename": "test.js"
}
```

You'll then recieve a response as follows:

```json
{
  "image_url": "https://code2image.up.railway.app/image/03d2eca8-e25a-446f-9a18-7e3c208f80f0",
  "page_url": "https://code2image.up.railway.app/page/03d2eca8-e25a-446f-9a18-7e3c208f80f0"
}
```

Go to both URIs and check them out! 💪
