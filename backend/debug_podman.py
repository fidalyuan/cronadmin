import asyncio
import json

async def test():
    cmd = "podman ps --format json"
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    print(f"STDOUT: {stdout.decode()}")
    print(f"STDERR: {stderr.decode()}")

if __name__ == "__main__":
    asyncio.run(test())
