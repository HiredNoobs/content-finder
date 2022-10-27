from collections import namedtuple  # for type hinting


def get_ascii_art(card: namedtuple) -> list:
    """Thanks to: https://codereview.stackexchange.com/questions/82103/ascii-fication-of-playing-cards"""
    special_mappings = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}

    suits = {'spades': '♠', 'diamonds': '♦', 'hearts': '♥', 'clubs': '♣'}

    lines = [[] for i in range(9)]

    if card.value == 10:
        rank = str(card.value)
        space = ''
    else:
        if card.value in special_mappings:
            rank = special_mappings[card.value][0]
        else:
            rank = str(card.value)[0]  # get first char

        space = '   '

    suit = suits[card.suit]

    # Awkward spacing is to deal with whatever Cytube is doing...
    lines[0].append('┌─────────┐')
    lines[1].append('│{}{}                  │'.format(rank, space))
    lines[2].append('│                       │')
    lines[3].append('│                       │')
    lines[4].append('│          {}           │'.format(suit))
    lines[5].append('│                       │')
    lines[6].append('│                       │')
    lines[7].append('│                  {}{}│'.format(space, rank))
    lines[8].append('└─────────┘')

    result = []
    for idx, _ in enumerate(lines):
        result.append(''.join(lines[idx]))

    return result


def get_hidden_ascii_art() -> list:
    lines = [
        '┌─────────┐',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '│░░░░░░░░░│',
        '└─────────┘',
    ]

    # for idx, line in enumerate(lines):
    #     lines[idx] = ''.join(line)

    return lines
