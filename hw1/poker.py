#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------
# Реализуйте функцию best_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. У каждой карты есть масть(suit) и
# ранг(rank)
# Масти: трефы(clubs, C), пики(spades, S), червы(hearts, H), бубны(diamonds, D)
# Ранги: 2, 3, 4, 5, 6, 7, 8, 9, 10 (ten, T), валет (jack, J), дама (queen, Q), король (king, K), туз (ace, A)
# Например: AS - туз пик (ace of spades), TH - дестяка черв (ten of hearts), 3C - тройка треф (three of clubs)

# Задание со *
# Реализуйте функцию best_wild_hand, которая принимает на вход
# покерную "руку" (hand) из 7ми карт и возвращает лучшую
# (относительно значения, возвращаемого hand_rank)
# "руку" из 5ти карт. Кроме прочего в данном варианте "рука"
# может включать джокера. Джокеры могут заменить карту любой
# масти и ранга того же цвета. Черный джокер '?B' может быть
# использован в качестве треф или пик любого ранга, красный
# джокер '?R' - в качестве черв и бубен люього ранга.

# Одна функция уже реализована, сигнатуры и описания других даны.
# Вам наверняка пригодится itertools
# Можно свободно определять свои функции и т.п.
# -----------------

import itertools


def hand_rank(hand):
    """Возвращает значение определяющее ранг 'руки'"""
    ranks = card_ranks(hand)
    if straight(ranks) and flush(hand):
        return (8, max(ranks))
    elif kind(4, ranks):
        return (7, kind(4, ranks), kind(1, ranks))
    elif kind(3, ranks) and kind(2, ranks):
        return (6, kind(3, ranks), kind(2, ranks))
    elif flush(hand):
        return (5, ranks)
    elif straight(ranks):
        return (4, max(ranks))
    elif kind(3, ranks):
        return (3, kind(3, ranks), ranks)
    elif two_pair(ranks):
        return (2, two_pair(ranks), ranks)
    elif kind(2, ranks):
        return (1, kind(2, ranks), ranks)
    else:
        return (0, ranks)


def card_ranks(hand):
    """Возвращает список рангов, отсортированный от большего к меньшему"""
    ranks = [rank_to_int(card[0]) for card in hand]
    return sorted(ranks, reverse=True)


def flush(hand):
    """Возвращает True, если все карты одной масти"""
    return len(set(c[1] for c in hand)) == 1


def straight(ranks):
    """Возвращает True, если отсортированные ранги формируют последовательность 5ти,
    где у 5ти карт ранги идут по порядку (стрит)"""
    n = 1
    for i in range(1, len(ranks)):
        if ranks[i-1] - ranks[i] == 1:
            n += 1
        else:
            n = 1
        if n == 5:
            return True
    return False


def kind(n, ranks):
    """Возвращает первый ранг, который n раз встречается в данной руке.
    Возвращает None, если ничего не найдено"""
    # Группировка 1 - доп. массив + сложность O(N)
    grouped = [0] * 15
    for rank in ranks:
        grouped[rank] += 1
    for i in range(len(grouped)-1, -1, -1):
        if grouped[i] == n:
            return i
    return None


def two_pair(ranks):
    """Если есть две пары, то возвращает два соответствующих ранга,
    иначе возвращает None"""
    # Группировка способом 2 - itertools
    pairs = []
    for rank, grouped in itertools.groupby(ranks):
        if len(list(grouped)) >= 2:
            pairs.append(rank)
    if len(pairs) >= 2:
        return pairs[:2]
    return None


def rank_to_int(rank):
    if rank == 'A':
        return 14
    if rank == 'K':
        return 13
    if rank == 'Q':
        return 12
    if rank == 'J':
        return 11
    if rank == 'T':
        return 10
    return int(rank)


def best_hand(hand):
    """Из "руки" в 7 карт возвращает лучшую "руку" в 5 карт"""
    # Всего возможных сочетаний: 21 = 7!/(5!*(7-5)!)
    combs = itertools.combinations(hand, 5)
    return max(combs, key=hand_rank)


def best_wild_hand(hand):
    """best_hand но с джокерами"""
    return


def test_card_ranks():
    print "test_card_ranks"
    assert (card_ranks("2S 5S 9S 4S TS QS AS JS KS".split())
            == [14, 13, 12, 11, 10, 9, 5, 4, 2])
    print "OK"


def test_flush():
    print "test_flush"
    assert flush("2S 5S 9S 4S TS QS AS JS KS".split()) is True
    assert flush("3S 4D 7C AS".split()) is False
    print "OK"


def test_straight():
    print "test_straight"
    assert straight([14, 13, 12, 11, 10]) is True
    assert straight([13, 12, 11, 10, 9]) is True
    assert straight([13, 11, 10, 9, 8]) is False
    assert straight([14, 12, 11, 10, 9]) is False
    assert straight([14, 10, 8, 6, 4]) is False
    print "OK"


def test_kind():
    print "test_kind"
    assert kind(4, [9, 9, 9, 9, 3]) == 9
    assert kind(3, [9, 9, 9, 9, 3]) == None
    assert kind(2, [9, 3, 3, 3, 2]) == None
    assert kind(1, [9, 8, 7, 6, 5]) == 9
    assert kind(5, [9, 9, 9, 9, 3]) == None
    assert kind(2, [9, 8, 7, 6, 5]) == None

    assert kind(3, [10, 10, 10, 8, 7]) == 10
    assert kind(2, [10, 10, 10, 8, 7]) == None
    print "OK"


def test_two_pairs():
    print "test_two_pairs"
    assert two_pair([14, 14, 13, 13, 13]) == [14, 13]
    assert two_pair([14, 14, 13, 12, 12]) == [14, 12]
    assert two_pair([14, 13, 13, 12, 11]) == None
    assert two_pair([14, 13, 12, 11, 11]) == None
    assert two_pair([14, 13, 12, 11, 10]) == None
    print "OK"


def test_best_hand():
    print "test_best_hand..."
    assert (sorted(best_hand("6C 7C 8C 9C TC 5C JS".split()))
            == ['6C', '7C', '8C', '9C', 'TC'])
    assert (sorted(best_hand("TD TC TH 7C 7D 8C 8S".split()))
            == ['8C', '8S', 'TC', 'TD', 'TH'])
    assert (sorted(best_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print 'OK'


def test_best_wild_hand():
    print "test_best_wild_hand..."
    assert (sorted(best_wild_hand("6C 7C 8C 9C TC 5C ?B".split()))
            == ['7C', '8C', '9C', 'JC', 'TC'])
    assert (sorted(best_wild_hand("TD TC 5H 5C 7C ?R ?B".split()))
            == ['7C', 'TC', 'TD', 'TH', 'TS'])
    assert (sorted(best_wild_hand("JD TC TH 7C 7D 7S 7H".split()))
            == ['7C', '7D', '7H', '7S', 'JD'])
    print 'OK'


if __name__ == '__main__':
    test_card_ranks()
    test_flush()
    test_straight()
    test_kind()
    test_two_pairs()
    test_best_hand()
    # test_best_wild_hand()

