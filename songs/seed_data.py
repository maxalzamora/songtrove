"""A starter library of public-domain songs.

Every sheet here is old enough to be free of copyright, which keeps the demo
data safe to publish. The set is deliberately varied: major and minor keys,
three time signatures, capo and no capo, ChordPro and one plain-text sheet, so
the library page has something to show on a fresh install.
"""

SONGS: tuple[dict, ...] = (
    {
        "title": "Amazing Grace",
        "artist": "John Newton",
        "song_key": "G",
        "capo": 0,
        "rating": 4,
        "status": "gig_ready",
        "tempo": 72,
        "time_signature": "3/4",
        "notes": "Verse one a cappella, then bring the guitar in on the pickup.",
        "tags": ("hymn", "waltz", "campfire"),
        "sheet_body": """\
[G]Amazing grace, how [G7]sweet the [C]sound
That [G]saved a wretch like [D]me
I [G]once was lost, but [G7]now am [C]found
Was [G]blind, but [D]now I [G]see

[G]'Twas grace that taught my [G7]heart to [C]fear
And [G]grace my fears re[D]lieved
How [G]precious did that [G7]grace ap[C]pear
The [G]hour I [D]first be[G]lieved

[G]Through many dangers, [G7]toils and [C]snares
I [G]have already [D]come
'Tis [G]grace hath brought me [G7]safe thus [C]far
And [G]grace will [D]lead me [G]home
""",
    },
    {
        "title": "House of the Rising Sun",
        "artist": "Traditional",
        "song_key": "A",
        "mode": "minor",
        "capo": 0,
        "rating": 3,
        "status": "practicing",
        "tempo": 78,
        "time_signature": "6/8",
        "notes": "Keep the right hand in a steady arpeggio and let the last verse "
        "drop to a whisper.",
        "tags": ("folk", "minor", "fingerpicking"),
        "sheet_body": """\
There is a [Am]house in [C]New Or[D]leans
They [F]call the [Am]Rising [E]Sun
And it's [Am]been the [C]ruin of [D]many a poor [F]boy
And [Am]God, I [E]know I'm [Am]one [E]

My [Am]mother was a [C]tailor [D]
She [F]sewed my [Am]new blue [E]jeans
My [Am]father was a [C]gamblin' [D]man
[F]Down in [Am]New Or[E]leans [Am] [E]

Oh [Am]mother, [C]tell your [D]children
Not to [F]do what [Am]I have [E]done
[Am]Spend your [C]lives in [D]sin and misery
In the [F]House of the [Am]Rising [E]Sun [Am]
""",
    },
    {
        "title": "Scarborough Fair",
        "artist": "Traditional",
        "song_key": "A",
        "mode": "minor",
        "capo": 0,
        "rating": 2,
        "status": "learning",
        "tempo": 92,
        "time_signature": "3/4",
        "notes": "The melody sits high in the chorus. Try it capoed up if the "
        "verse feels low.",
        "tags": ("folk", "minor", "waltz"),
        "sheet_body": """\
[Am]Are you going to [G]Scarborough [Am]Fair?
[Am]Parsley, [C]sage, rose[G]mary and [Am]thyme
Re[Am]member me [C]to one who [G]lives there
[Am]She once [G]was a true love of [Am]mine

[Am]Tell her to make me a [G]cambric [Am]shirt
[Am]Parsley, [C]sage, rose[G]mary and [Am]thyme
With[Am]out no seams nor [C]needle[G]work
[Am]Then she'll [G]be a true love of [Am]mine
""",
    },
    {
        "title": "Wayfaring Stranger",
        "artist": "Traditional",
        "song_key": "A",
        "mode": "minor",
        "capo": 0,
        "rating": 4,
        "status": "practicing",
        "tempo": 84,
        "time_signature": "4/4",
        "notes": "Hold the Dm chord a full bar at the end of each verse before "
        "walking back down.",
        "tags": ("folk", "minor", "ballad"),
        "sheet_body": """\
I'm just a [Am]poor wayfaring [C]stranger
While [Dm]traveling through this [Am]world of woe
Yet [Am]there's no sickness, [C]toil nor danger
In [Dm]that bright land to [E]which I [Am]go

I'm [Am]going there to see my [C]Father
I'm [Dm]going there no more to [Am]roam
I'm [Am]just a-going over [C]Jordan
I'm [Dm]just a-going [E]over [Am]home
""",
    },
    {
        "title": "Shenandoah",
        "artist": "Traditional",
        "song_key": "D",
        "capo": 2,
        "rating": 5,
        "status": "gig_ready",
        "tempo": 66,
        "time_signature": "4/4",
        "notes": "Capo two keeps the open D shapes ringing. Slow the last line "
        "right down.",
        "tags": ("folk", "ballad", "campfire"),
        "sheet_body": """\
Oh [D]Shenan[G]doah, I [D]long to [A]hear you
A[D]way, you [G]rolling [D]river
Oh [D]Shenan[G]doah, I [D]long to [A]hear you
A[D]way, I'm [A]bound a[D]way

Oh [D]Shenan[G]doah, I [D]love your [A]daughter
A[D]way, you [G]rolling [D]river
And [D]I will [G]take her [D]down the [A]river
A[D]way, I'm [A]bound a[D]way
""",
    },
    {
        "title": "Down in the Valley",
        "artist": "Traditional",
        "song_key": "G",
        "capo": 2,
        "rating": 3,
        "status": "learning",
        "tempo": 96,
        "time_signature": "4/4",
        "notes": "Good one for practising a bass note on the beat and a light "
        "strum between.",
        "tags": ("folk", "campfire", "fingerpicking"),
        "sheet_body": """\
[G]Down in the valley, the [C]valley so [G]low
Hang your head [Em]over, hear the [D]wind [D7]blow
Hear the [G]wind blow, dear, hear the [C]wind [G]blow
Hang your head [D]over, hear the [D7]wind [G]blow

[G]Roses love sunshine, [C]violets love [G]dew
Angels in [Em]heaven know I [D]love you [D7]
Hear the [G]wind blow, dear, hear the [C]wind [G]blow
Hang your head [D]over, hear the [D7]wind [G]blow
""",
    },
    {
        "title": "The Water Is Wide",
        "artist": "Traditional",
        "song_key": "D",
        "capo": 0,
        "rating": 4,
        "status": "practicing",
        "tempo": 68,
        "time_signature": "3/4",
        "notes": "Let the A chord at the end of each line ring instead of "
        "rushing into the next verse.",
        "tags": ("folk", "ballad", "waltz"),
        "sheet_body": """\
The [D]water is [G]wide, I [D]can't cross [A]o'er
And [D]neither have I [G]wings to [A]fly
Give me a [D]boat that [G]will carry [D]two
And [A]both shall [D]row, my [A]love and [D]I

The [D]water is [G]wide, and [D]deep and [A]wide
And [D]I have loved a [G]false true [A]love
I'll [D]give her [G]back to the [D]waters [A]wide
And [D]let her [A]go where [D]she will [A]rove
""",
    },
    {
        "title": "Shady Grove",
        "artist": "Traditional",
        "song_key": "A",
        "mode": "minor",
        "capo": 0,
        "rating": 2,
        "status": "idea",
        "tempo": 112,
        "time_signature": "4/4",
        "notes": "A plain-text sheet on purpose: old songbooks often look like "
        "this, and SongTrove reads them as-is.",
        "tags": ("folk", "minor", "flatpicking"),
        "sheet_format": "plain",
        "sheet_body": """\
Am        C
Shady Grove, my little love
Am        G
Shady Grove, I say
Am        C
Shady Grove, my little love
G         Am
Going to Marbletown

Am        C
Cheeks as red as a blooming rose
Am        G
Eyes are the prettiest brown
Am        C
She's the darling of my heart
G         Am
She lives in Marbletown
""",
    },
)
