from datetime import datetime, timedelta


SM2_MIN_EASE = 1.3
FIRST_INTERVAL_MINUTES = 10


def sm2_update(
    repetition_before: int,
    interval_before: int,
    ease_before: float,
    quality: int,
    reviewed_at: datetime,
) -> dict:
    
    # Should already be enforced via schema, but check to be sure
    if quality < 0 or quality > 5:
        raise ValueError("quality must be between 0 and 5")

    repetition = repetition_before
    interval = interval_before
    ease = ease_before

    # Ease factor update (apply on all reviews, including failures)
    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ease < SM2_MIN_EASE:
        ease = SM2_MIN_EASE

    # Failed review -> relearn soon
    if quality < 3:
        repetition = 0
        interval = 0
        next_review_at = reviewed_at + timedelta(minutes=FIRST_INTERVAL_MINUTES)

    # Initial successful learning review
    elif repetition == 0:
        interval = 0

        # Short interval
        next_review_at = reviewed_at + timedelta(minutes=FIRST_INTERVAL_MINUTES)
        repetition += 1

    # Successful regular review, proceed to normal intervals
    else:

        if repetition == 1: interval = 1
        elif repetition == 2: interval = 6
        else: interval = round(interval * ease)

        # Update interval normally
        next_review_at = reviewed_at + timedelta(days=interval)   
        repetition += 1

    return {
        "repetition_count": repetition,
        "interval_days": interval,
        "ease_factor": ease,
        "next_review_at": next_review_at,
    }