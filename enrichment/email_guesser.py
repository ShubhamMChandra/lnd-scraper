"""
Email pattern guesser + SMTP verification.
Given a name and domain, generates common email patterns and verifies
which one actually exists using SMTP RCPT TO checks.
"""
import logging
import smtplib
import dns.resolver
import socket
import time
from typing import Optional

logger = logging.getLogger("enrichment.email_guesser")


def _generate_patterns(first: str, last: str, domain: str) -> list[str]:
    """Generate common corporate email patterns."""
    f = first.lower().strip()
    l = last.lower().strip()
    fi = f[0] if f else ""
    li = l[0] if l else ""

    patterns = [
        f"{f}.{l}@{domain}",       # jane.doe@
        f"{f}{l}@{domain}",        # janedoe@
        f"{fi}{l}@{domain}",       # jdoe@
        f"{f}@{domain}",           # jane@
        f"{f}_{l}@{domain}",       # jane_doe@
        f"{fi}.{l}@{domain}",      # j.doe@
        f"{l}{fi}@{domain}",       # doej@
        f"{l}.{f}@{domain}",       # doe.jane@
        f"{l}@{domain}",           # doe@
        f"{f}{li}@{domain}",       # janem@
        f"{fi}{li}@{domain}",      # jd@
    ]
    return patterns


def _get_mx_host(domain: str) -> Optional[str]:
    """Get the MX server for a domain."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        # Get highest priority (lowest preference number) MX record
        mx_records = sorted(answers, key=lambda r: r.preference)
        if mx_records:
            return str(mx_records[0].exchange).rstrip(".")
        return None
    except Exception:
        return None


def _verify_email_smtp(email: str, mx_host: str) -> bool:
    """
    Verify an email exists using SMTP RCPT TO.
    Returns True if the server accepts the recipient.
    """
    try:
        smtp = smtplib.SMTP(timeout=10)
        smtp.connect(mx_host, 25)
        smtp.helo("verify.local")
        smtp.mail("check@verify.local")
        code, _ = smtp.rcpt(email)
        smtp.quit()
        # 250 = accepted, 251 = forwarded (both good)
        return code in (250, 251)
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
            socket.timeout, socket.error, OSError):
        return False
    except Exception as e:
        logger.debug(f"SMTP verify error for {email}: {e}")
        return False


# Cache MX lookups and catch-all status per domain
_mx_cache: dict[str, Optional[str]] = {}
_catchall_cache: dict[str, bool] = {}


def _is_catchall(domain: str, mx_host: str) -> bool:
    """Check if domain is a catch-all (accepts any email)."""
    if domain in _catchall_cache:
        return _catchall_cache[domain]

    # Test with a random nonexistent address
    fake = f"zzznonexistent12345@{domain}"
    result = _verify_email_smtp(fake, mx_host)
    _catchall_cache[domain] = result
    if result:
        logger.debug(f"{domain} is catch-all, SMTP verification unreliable")
    return result


def guess_email(first_name: str, last_name: str, domain: str) -> Optional[str]:
    """
    Guess and verify an email address given a name and domain.
    Returns the first verified email, or the most common pattern if
    SMTP verification isn't possible.
    """
    if not first_name or not last_name or not domain:
        return None

    # Clean names (remove suffixes like ", MBA" or ", PHR")
    first = first_name.split(",")[0].split("(")[0].strip()
    last = last_name.split(",")[0].split("(")[0].strip()

    # Handle multi-word last names - use last word
    if " " in last:
        last = last.split()[-1]

    patterns = _generate_patterns(first, last, domain)

    # Try to get MX record
    if domain not in _mx_cache:
        _mx_cache[domain] = _get_mx_host(domain)

    mx_host = _mx_cache[domain]

    if not mx_host:
        # Can't verify, return most common pattern
        logger.debug(f"No MX for {domain}, returning best guess")
        return patterns[0]  # first.last@ is most common

    # Check if catch-all
    if _is_catchall(domain, mx_host):
        # Can't distinguish, return best guess
        return patterns[0]

    # Try each pattern via SMTP
    for email in patterns:
        if _verify_email_smtp(email, mx_host):
            logger.info(f"Verified email: {email}")
            return email
        time.sleep(0.5)  # Be polite between checks

    # None verified - return best guess anyway (SMTP may be blocking)
    logger.debug(f"No SMTP verification for {first} {last} @ {domain}, using best guess")
    return patterns[0]
