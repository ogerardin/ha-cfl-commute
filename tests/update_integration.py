#!/usr/bin/env python3
"""Update CFL Commute integration via HACS.

Checks version, redownloads if needed, and restarts HA.
"""

import asyncio
import os
import subprocess
import sys
import socket

import aiohttp
from dotenv import load_dotenv

load_dotenv()


def get_ha_ip():
    try:
        ip = socket.gethostbyname("homeassistant.lan")
        return f"http://{ip}:8123"
    except:
        return "http://homeassistant.lan:8123"


HA_URL = get_ha_ip()
HA_TOKEN = os.getenv("HA_TOKEN")


def get_local_version() -> str:
    """Get git commit hash as version (what HACS tracks)."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    return result.stdout.strip()


async def check_ha_available(timeout: int = 10) -> bool:
    """Check if Home Assistant is available."""
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HA_URL}/api/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                return response.status == 200
    except Exception:
        return False


async def wait_for_ha(timeout: int = 120) -> bool:
    """Wait for HA to be available after restart."""
    print(f"Waiting for HA to restart (max {timeout}s)...")
    for i in range(timeout // 5):
        if await check_ha_available():
            print(f"HA is back up after {(i + 1) * 5}s")
            return True
        await asyncio.sleep(5)
    print("HA did not come back within timeout")
    return False


async def restart_ha() -> None:
    """Restart Home Assistant."""
    print("Restarting Home Assistant...")
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{HA_URL}/api/services/homeassistant/restart",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                print(f"Restart API response: {response.status}")
    except Exception as e:
        print(f"Restart error: {e}")


async def check_integration_version() -> tuple[str | None, bool, bool]:
    """Check if CFL Commute is installed, get version, and restart status.

    Returns: (version, found, restart_required)
    """
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HA_URL}/api/states/update.cfl_commute_update",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    state = await response.json()
                    attrs = state.get("attributes", {})
                    version = attrs.get("installed_version", None)
                    release_summary = attrs.get("release_summary", "") or ""
                    restart_required = (
                        "Restart of Home Assistant required" in release_summary
                    )
                    return (version, True, restart_required)
                elif response.status == 404:
                    return (None, False, False)
    except Exception as e:
        print(f"Could not check states: {e}")
    return (None, False, False)
    return (None, False)


async def redownload_via_hacs(local_version: str) -> bool:
    """Redownload CFL Commute via HACS API with retry logic."""
    print("Starting HACS update via API...")
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}

    # Get installed version BEFORE triggering update
    initial_version = None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HA_URL}/api/states/update.cfl_commute_update",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    state = await resp.json()
                    initial_version = state.get("attributes", {}).get(
                        "installed_version"
                    )
                    print(f"Current installed version: {initial_version}")
    except Exception as e:
        print(f"Could not get initial version: {e}")

    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                # Trigger update via update/install service
                print(f"Attempt {attempt + 1}: Triggering update/install service...")
                payload = {"entity_id": "update.cfl_commute_update"}

                async with session.post(
                    f"{HA_URL}/api/services/update/install",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    print(f"Update response: {response.status}")

                    # 200/201 = success, 500 may mean HACS is still processing
                    if response.status not in (200, 201, 500):
                        if attempt < 2:
                            print(f"Retrying in 10 seconds...")
                            await asyncio.sleep(10)
                            continue
                        print(f"Update failed with status {response.status}")
                        return False

                # Wait for update to complete
                print("Waiting for update to complete...")
                for i in range(120):  # Wait up to 120 seconds
                    try:
                        async with session.get(
                            f"{HA_URL}/api/states/update.cfl_commute_update",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status == 200:
                                state = await resp.json()
                                attrs = state.get("attributes", {})
                                in_progress = attrs.get("in_progress", False)
                                percentage = attrs.get("update_percentage")
                                installed = attrs.get("installed_version")
                                latest = attrs.get("latest_version")

                                if percentage is not None:
                                    print(f"  Progress: {percentage}%")

                                if not in_progress:
                                    # Check if version actually changed
                                    if installed != initial_version:
                                        if installed == local_version:
                                            print(
                                                f"✓ Update complete! Installed: {installed}"
                                            )
                                            return True
                                        else:
                                            print(
                                                f"✗ Update installed but mismatch. Installed: {installed}, Expected: {local_version}"
                                            )
                                            return False
                                    else:
                                        # Version hasn't changed - update may have failed
                                        if response.status == 500:
                                            # HACS returned 500 but version didn't change - likely failed
                                            print(
                                                f"✗ Update failed (version unchanged after HACS 500). Installed: {installed}"
                                            )
                                            if attempt < 2:
                                                print("Retrying in 15 seconds...")
                                                await asyncio.sleep(15)
                                                break  # Break inner loop to retry
                                            return False
                                        else:
                                            print(
                                                f"✗ Update failed. Installed: {installed}, Expected: {local_version}"
                                            )
                                            return False
                    except Exception as e:
                        print(f"Status check error: {e}")

                    await asyncio.sleep(1)

                if attempt < 2:
                    print("Retrying...")
                    await asyncio.sleep(10)
                    continue
                return False

        except asyncio.TimeoutError:
            print(f"Attempt {attempt + 1} timed out")
            if attempt < 2:
                await asyncio.sleep(10)
                continue
            return False
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(10)
                continue
            return False

    return False


async def main():
    if not HA_TOKEN:
        print("Error: HA_TOKEN not found in .env")
        sys.exit(1)

    # Check HA is available first
    if not await check_ha_available():
        print("Error: Home Assistant is not available")
        sys.exit(1)

    local_version = get_local_version()
    print(f"Local version: {local_version}")
    print("=" * 50)

    # Check current installed version
    version, found, restart_required = await check_integration_version()

    if found:
        print(f"Installed version: {version}")

        # Check if restart is needed even with matching versions
        if restart_required:
            print("⚠ Restart required to apply pending changes")
            print("→ Restarting Home Assistant...")
            await restart_ha()
            if await wait_for_ha():
                print("✓ HA restarted successfully")
            else:
                print("✗ HA restart failed or timed out")
                print("→ Please restart HA manually if needed")
        elif version != local_version:
            print(f"Version mismatch! Local: {local_version}, Installed: {version}")
            print("→ Redownloading...")

            # Redownload via HACS
            success = await redownload_via_hacs(local_version)
            if success:
                print("✓ Redownload completed")
                print("→ Restarting Home Assistant...")
                await restart_ha()
                if await wait_for_ha():
                    print("✓ HA restarted successfully")
                else:
                    print("✗ HA restart failed or timed out")
                    print("→ Please restart HA manually if needed")
            else:
                print("✗ Redownload failed")
                print("→ Try restarting HA manually or updating via HACS UI")
                sys.exit(1)
        else:
            print(f"✓ Version up to date ({local_version})")
            print("→ No update needed")
    else:
        print("CFL Commute not installed")
        print("→ Please install via HACS first")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
