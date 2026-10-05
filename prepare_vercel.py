import os
import json

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend"

# 1. Update server.ts
server_path = os.path.join(base_dir, "src/server.ts")
with open(server_path, "r") as f:
    server_content = f.read()

# Replace the app.listen part to be compatible with Vercel Serverless
if "app.listen(PORT," in server_content and "export default app;" not in server_content:
    old_listen = "app.listen(PORT, () => {"
    new_listen = """if (!process.env.VERCEL) {
  app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

export default app;"""
    # Just a quick regex/replace
    import re
    server_content = re.sub(r'app\.listen\(PORT, \(\) => \{.*?\}\);', new_listen, server_content, flags=re.DOTALL)
    
    with open(server_path, "w") as f:
        f.write(server_content)

# 2. Update package.json to add postinstall for Prisma in Vercel
pkg_path = os.path.join(base_dir, "package.json")
with open(pkg_path, "r") as f:
    pkg = json.load(f)

pkg["scripts"]["postinstall"] = "prisma generate"

with open(pkg_path, "w") as f:
    json.dump(pkg, f, indent=2)

# 3. Create vercel.json
vercel_path = os.path.join(base_dir, "vercel.json")
vercel_config = {
  "version": 2,
  "builds": [
    {
      "src": "src/server.ts",
      "use": "@vercel/node"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "src/server.ts"
    }
  ]
}

with open(vercel_path, "w") as f:
    json.dump(vercel_config, f, indent=2)

print("Vercel configuration completed.")
