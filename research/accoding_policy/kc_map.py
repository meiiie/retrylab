"""Author-defined grouping of the 96 released ACcoding tags into course-level skills.

The dataset paper (Scientific Data 2024, doi:10.1038/s41597-024-03392-z) states
that knowledge-point tags were defined by educators or teaching assistants; it
does not publish an annotation protocol or agreement statistics. Grouping the
tags into fifteen skills is a documented modelling decision by this study's
authors, not an expert-validated knowledge-component model. Linked lists are
grouped with pointers because in C they are the canonical pointer application.
"""

# skill key -> (English display name, Vietnamese display name)
SKILLS = {
    'basics': ('Basic syntax, I/O and data types', 'Cú pháp cơ bản, nhập xuất, kiểu dữ liệu'),
    'conditionals': ('Conditionals', 'Rẽ nhánh'),
    'loops': ('Loops', 'Vòng lặp'),
    'arrays': ('Arrays', 'Mảng'),
    'strings': ('Strings', 'Xâu ký tự'),
    'pointers': ('Pointers and linked lists', 'Con trỏ và danh sách liên kết'),
    'bits': ('Bit operations and number bases', 'Phép toán bit và hệ cơ số'),
    'arithmetic': ('Arithmetic and number theory', 'Tính toán số học và số học'),
    'recursion': ('Recursion, recurrence and divide-and-conquer', 'Đệ quy, truy hồi và chia để trị'),
    'sorting_search': ('Sorting and searching', 'Sắp xếp và tìm kiếm'),
    'greedy_sim': ('Greedy, brute force and simulation', 'Tham lam, vét cạn và mô phỏng'),
    'dp': ('Dynamic programming', 'Quy hoạch động'),
    'data_structures': ('Data structures', 'Cấu trúc dữ liệu'),
    'graphs': ('Graphs', 'Đồ thị'),
    'geometry_adv': ('Geometry and advanced mathematics', 'Hình học và toán nâng cao'),
}
UNTAGGED = 'untagged'
SKILL_KEYS = list(SKILLS) + [UNTAGGED]

# Introductory C-programming skills eligible for the recommendation scenario.
FUNDAMENTALS = ['basics', 'conditionals', 'loops', 'arrays', 'strings', 'pointers',
                'bits', 'arithmetic', 'recursion', 'sorting_search']
# Skills assessed by the held-out post-test (basics and arithmetic are too broad).
POSTTEST_SKILLS = ['conditionals', 'loops', 'arrays', 'strings', 'pointers',
                   'bits', 'recursion', 'sorting_search']

# released tag id -> (skill key, English tag translation by the authors)
TAGS = {
    1: ('basics', 'input/output'), 3: ('basics', 'data types'), 41: ('basics', 'escape characters'),
    96: ('basics', 'A+B / starter problems'), 142: ('basics', 'code basics'), 30: ('basics', 'floating-point precision'),
    175: ('conditionals', 'conditionals'),
    138: ('loops', 'loops'),
    185: ('arrays', 'arrays'),
    12: ('strings', 'strings'), 237: ('strings', 'string matching'),
    94: ('pointers', 'pointers'), 9: ('pointers', 'linked lists'),
    8: ('bits', 'bitwise operations'), 80: ('bits', 'binary'), 52: ('bits', 'number bases'), 91: ('bits', 'Hamming distance'),
    104: ('arithmetic', 'math computation'), 27: ('arithmetic', 'number theory'), 173: ('arithmetic', 'modulo'),
    205: ('arithmetic', 'primes'), 92: ('arithmetic', 'greatest common divisor'), 230: ('arithmetic', 'Euclidean algorithm'),
    208: ('arithmetic', 'narcissistic numbers'), 167: ('arithmetic', 'big-number arithmetic'), 56: ('arithmetic', 'power computation'),
    22: ('arithmetic', 'fast exponentiation'), 6: ('arithmetic', 'date and time calculation'), 125: ('arithmetic', 'derangements'),
    330: ('arithmetic', "Horner's rule"), 42: ('arithmetic', 'polynomials'), 64: ('arithmetic', 'complex numbers'),
    19: ('arithmetic', 'matrices/determinants'), 265: ('arithmetic', 'probability and statistics'), 73: ('arithmetic', 'sets'),
    4: ('recursion', 'recursion'), 18: ('recursion', 'recurrence'), 72: ('recursion', 'Tower of Hanoi'),
    114: ('recursion', 'Fibonacci sequence'), 17: ('recursion', 'divide and conquer'), 5: ('recursion', 'backtracking'),
    16: ('sorting_search', 'sorting'), 79: ('sorting_search', 'bubble sort'), 39: ('sorting_search', 'quicksort'),
    43: ('sorting_search', 'merge sort'), 70: ('sorting_search', 'inversion pairs'), 40: ('sorting_search', 'binary search'),
    221: ('sorting_search', 'binary search (lookup)'), 164: ('sorting_search', 'binary search on the answer'),
    7: ('sorting_search', 'search'), 87: ('sorting_search', 'depth-first search'),
    279: ('greedy_sim', 'greedy'), 264: ('greedy_sim', 'local greedy'), 23: ('greedy_sim', 'brute force'),
    21: ('greedy_sim', 'simulation'), 31: ('greedy_sim', 'pruning'), 242: ('greedy_sim', 'fractional knapsack'),
    47: ('greedy_sim', 'flow-shop scheduling'),
    24: ('dp', 'dynamic programming'), 54: ('dp', '0/1 knapsack'), 65: ('dp', 'unbounded knapsack'),
    83: ('dp', 'bounded knapsack'), 244: ('dp', 'knapsack problems'), 168: ('dp', 'longest increasing subsequence'),
    174: ('dp', 'longest common subsequence'), 241: ('dp', 'probability DP'), 356: ('dp', 'expectation DP'),
    122: ('data_structures', 'data structures'), 10: ('data_structures', 'stack'), 11: ('data_structures', 'queue'),
    53: ('data_structures', 'heap'), 71: ('data_structures', 'priority queue'), 14: ('data_structures', 'tree'),
    357: ('data_structures', 'binary tree'), 63: ('data_structures', 'binary search tree'), 95: ('data_structures', 'hash table'),
    231: ('data_structures', 'trie'), 59: ('data_structures', 'segment tree'), 49: ('data_structures', 'union-find'),
    223: ('data_structures', 'STL'), 34: ('data_structures', 'Huffman coding'),
    15: ('graphs', 'graph theory'), 74: ('graphs', 'shortest paths'), 50: ('graphs', 'minimum spanning tree'),
    75: ('graphs', 'Floyd-Warshall algorithm'), 232: ('graphs', 'maximum flow'), 233: ('graphs', 'bipartite matching'),
    26: ('geometry_adv', 'computational geometry'), 37: ('geometry_adv', 'convex hull'), 313: ('geometry_adv', 'mathematical geometry'),
    281: ('geometry_adv', 'cross product'), 345: ('geometry_adv', 'dot product'), 25: ('geometry_adv', 'fast Fourier transform'),
    81: ('geometry_adv', 'convolution'), 298: ('geometry_adv', 'inversion transform'), 2: ('geometry_adv', 'game theory'),
}


def skill_weights(tag_weights):
    """Map {tag_id: weight} to normalized {skill: weight}; unknown or empty -> untagged."""
    total = {}
    for tag, weight in tag_weights.items():
        if tag not in TAGS:
            raise KeyError(f'Unmapped released tag id {tag}')
        skill = TAGS[tag][0]
        total[skill] = total.get(skill, 0.0) + (weight if weight and weight > 0 else 1.0)
    if not total:
        return {UNTAGGED: 1.0}
    norm = sum(total.values())
    return {k: v / norm for k, v in total.items()}


def primary_skill(weights):
    return max(sorted(weights), key=lambda k: weights[k])
