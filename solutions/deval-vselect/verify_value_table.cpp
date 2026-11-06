#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <immintrin.h>
#include <numeric>
#include <vector>
#include <iostream>
using u64=std::uint64_t;
struct PosetClass {
    u64 relation;
    int sum;
};
// clang-format off
constexpr PosetClass kPosetClasses[318] = {
    {0x0ULL, 0}, {0x10101010100ULL, 600}, {0x10102020000ULL, 960}, {0x10202020000ULL, 900},
    {0x10204000000ULL, 1080}, {0x20202020000ULL, 576}, {0x20404000000ULL, 840}, {0x30102020000ULL, 1020},
    {0x30202020000ULL, 936}, {0x30301020000ULL, 1080}, {0x30302020000ULL, 1056}, {0x30303020000ULL, 1116},
    {0x30303030000ULL, 1152}, {0x30303030100ULL, 1176}, {0x30306020000ULL, 1394}, {0x30404000000ULL, 1000},
    {0x30505010100ULL, 1440}, {0x30506000000ULL, 1380}, {0x30604000000ULL, 1239}, {0x30606020000ULL, 1398},
    {0x30a02010000ULL, 1336}, {0x30a02020000ULL, 1278}, {0x30c00000000ULL, 1120}, {0x30c04000000ULL, 1300},
    {0x40404000000ULL, 540}, {0x40800000000ULL, 720}, {0x50204000000ULL, 1140}, {0x50505010100ULL, 1140},
    {0x50604000000ULL, 1214}, {0x50606000000ULL, 1324}, {0x50901010100ULL, 1320}, {0x50a02010000ULL, 1500},
    {0x60204000000ULL, 954}, {0x60404000000ULL, 892}, {0x60601000000ULL, 1240}, {0x60604000000ULL, 1010},
    {0x60606000000ULL, 1068}, {0x60606020000ULL, 1110}, {0x60800000000ULL, 900}, {0x60a02020000ULL, 1280},
    {0x60c04000000ULL, 1210}, {0x70204000000ULL, 1164}, {0x70303020000ULL, 1406}, {0x70304000000ULL, 1306},
    {0x70305010100ULL, 1524}, {0x70306020000ULL, 1481}, {0x70404000000ULL, 1004}, {0x70505010100ULL, 1452},
    {0x70506000000ULL, 1404}, {0x70604000000ULL, 1250}, {0x70606000000ULL, 1340}, {0x70606020000ULL, 1416},
    {0x70703020000ULL, 1516}, {0x70704000000ULL, 1332}, {0x70705010100ULL, 1560}, {0x70706000000ULL, 1436},
    {0x70706020000ULL, 1520}, {0x70707000000ULL, 1476}, {0x70707010100ULL, 1608}, {0x70707020000ULL, 1566},
    {0x70707030000ULL, 1632}, {0x70707030100ULL, 1680}, {0x70800000000ULL, 960}, {0x70901010100ULL, 1440},
    {0x70a02020000ULL, 1396}, {0x70b01020000ULL, 1558}, {0x70b02020000ULL, 1476}, {0x70b03020000ULL, 1639},
    {0x70b03030000ULL, 1720}, {0x70b03030100ULL, 1800}, {0x70c04000000ULL, 1316}, {0x70d05010100ULL, 1710},
    {0x70e04000000ULL, 1396}, {0x70e06000000ULL, 1544}, {0x70e06020000ULL, 1659}, {0x80800000000ULL, 480},
    {0x90901010100ULL, 1080}, {0xa0a02010000ULL, 1340}, {0xa0a02020000ULL, 1050}, {0xa0c00000000ULL, 1084},
    {0xb0301020000ULL, 1348}, {0xb0302020000ULL, 1308}, {0xb0601020000ULL, 1529}, {0xb0a02010000ULL, 1423},
    {0xb0a02020000ULL, 1316}, {0xb0b01020000ULL, 1458}, {0xb0b02020000ULL, 1402}, {0xb0b03020000ULL, 1514},
    {0xb0b03030000ULL, 1572}, {0xb0b03030100ULL, 1620}, {0xb0c00000000ULL, 1170}, {0xb0d01010100ULL, 1524},
    {0xb0e02020000ULL, 1481}, {0xc0800000000ULL, 810}, {0xc0c00000000ULL, 920}, {0xc0c04000000ULL, 1000},
    {0xd0604000000ULL, 1325}, {0xd0901010100ULL, 1350}, {0xd0d01010100ULL, 1440}, {0xd0d05010100ULL, 1560},
    {0xd0e00000000ULL, 1228}, {0xd0e04000000ULL, 1408}, {0xe0302020000ULL, 1398}, {0xe0304000000ULL, 1379},
    {0xe0604000000ULL, 1241}, {0xe0800000000ULL, 912}, {0xe0a02020000ULL, 1311}, {0xe0c00000000ULL, 1120},
    {0xe0c04000000ULL, 1252}, {0xe0e00000000ULL, 1188}, {0xe0e02020000ULL, 1400}, {0xe0e04000000ULL, 1334},
    {0xe0e06000000ULL, 1440}, {0xe0e06020000ULL, 1520}, {0xf0301020000ULL, 1456}, {0xf0302020000ULL, 1410},
    {0xf0304000000ULL, 1412}, {0xf0604000000ULL, 1340}, {0xf0703020000ULL, 1679}, {0xf0704000000ULL, 1432},
    {0xf0705010100ULL, 1746}, {0xf0706000000ULL, 1580}, {0xf0706020000ULL, 1693}, {0xf0800000000ULL, 966},
    {0xf0901010100ULL, 1452}, {0xf0a02010000ULL, 1568}, {0xf0a02020000ULL, 1411}, {0xf0b01020000ULL, 1603},
    {0xf0b02020000ULL, 1515}, {0xf0b03020000ULL, 1684}, {0xf0b03030000ULL, 1760}, {0xf0b03030100ULL, 1836},
    {0xf0c00000000ULL, 1192}, {0xf0c04000000ULL, 1340}, {0xf0d01010100ULL, 1560}, {0xf0d05010100ULL, 1752},
    {0xf0e00000000ULL, 1260}, {0xf0e02020000ULL, 1518}, {0xf0e04000000ULL, 1440}, {0xf0e06000000ULL, 1592},
    {0xf0e06020000ULL, 1704}, {0xf0f00000000ULL, 1296}, {0xf0f01010100ULL, 1608}, {0xf0f01020000ULL, 1668},
    {0xf0f02020000ULL, 1564}, {0xf0f03020000ULL, 1754}, {0xf0f03030000ULL, 1840}, {0xf0f03030100ULL, 1920},
    {0xf0f04000000ULL, 1484}, {0xf0f05010100ULL, 1824}, {0xf0f06000000ULL, 1652}, {0xf0f06020000ULL, 1770},
    {0xf0f07000000ULL, 1728}, {0xf0f07010100ULL, 1920}, {0xf0f07020000ULL, 1856}, {0xf0f07030000ULL, 1960},
    {0xf0f07030100ULL, 2040}, {0x100000000000ULL, 360}, {0x110101010100ULL, 960}, {0x110102020000ULL, 1220},
    {0x120201020000ULL, 1220}, {0x120202020000ULL, 930}, {0x130102020000ULL, 1232}, {0x130201020000ULL, 1250},
    {0x130202020000ULL, 1050}, {0x130301020000ULL, 1336}, {0x130302020000ULL, 1278}, {0x130303020000ULL, 1394},
    {0x130303030000ULL, 1452}, {0x130303030100ULL, 1500}, {0x130306020000ULL, 1610}, {0x140402000000ULL, 1110},
    {0x140404000000ULL, 880}, {0x150402000000ULL, 1230}, {0x150503010100ULL, 1680}, {0x150505010100ULL, 1440},
    {0x160204000000ULL, 1140}, {0x160404000000ULL, 1000}, {0x160601000000ULL, 1380}, {0x160603020000ULL, 1624},
    {0x160604000000ULL, 1217}, {0x160605000000ULL, 1516}, {0x160606000000ULL, 1324}, {0x160606020000ULL, 1402},
    {0x170204000000ULL, 1242}, {0x170303020000ULL, 1514}, {0x170304000000ULL, 1408}, {0x170305010100ULL, 1710},
    {0x170306020000ULL, 1644}, {0x170404000000ULL, 1060}, {0x170505010100ULL, 1560}, {0x170506000000ULL, 1548},
    {0x170603020000ULL, 1653}, {0x170604000000ULL, 1330}, {0x170606000000ULL, 1436}, {0x170606020000ULL, 1518},
    {0x170703020000ULL, 1694}, {0x170704000000ULL, 1436}, {0x170705010100ULL, 1752}, {0x170706000000ULL, 1592},
    {0x170706020000ULL, 1696}, {0x170707000000ULL, 1644}, {0x170707010100ULL, 1824}, {0x170707020000ULL, 1763},
    {0x170707030000ULL, 1858}, {0x170707030100ULL, 1932}, {0x180000000000ULL, 600}, {0x180800000000ULL, 780},
    {0x190101010100ULL, 1080}, {0x190901010100ULL, 1320}, {0x1a0202010000ULL, 1340}, {0x1a0202020000ULL, 1050},
    {0x1a0a02010000ULL, 1540}, {0x1a0a02020000ULL, 1285}, {0x1b0102020000ULL, 1340}, {0x1b0202010000ULL, 1352},
    {0x1b0202020000ULL, 1110}, {0x1b0301020000ULL, 1456}, {0x1b0302020000ULL, 1398}, {0x1b0303020000ULL, 1514},
    {0x1b0303030000ULL, 1572}, {0x1b0303030100ULL, 1620}, {0x1b0a02010000ULL, 1569}, {0x1b0a02020000ULL, 1401},
    {0x1b0b01020000ULL, 1610}, {0x1b0b02020000ULL, 1517}, {0x1b0b03020000ULL, 1682}, {0x1b0b03030000ULL, 1766},
    {0x1b0b03030100ULL, 1830}, {0x1c0000000000ULL, 660}, {0x1c0404000000ULL, 1000}, {0x1c0800000000ULL, 900},
    {0x1c0c00000000ULL, 1080}, {0x1c0c04000000ULL, 1220}, {0x1d0101010100ULL, 1140}, {0x1d0505010100ULL, 1560},
    {0x1d0901010100ULL, 1440}, {0x1d0d01010100ULL, 1560}, {0x1d0d05010100ULL, 1740}, {0x1e0000000000ULL, 696},
    {0x1e0202020000ULL, 1110}, {0x1e0204000000ULL, 1230}, {0x1e0404000000ULL, 1060}, {0x1e0604000000ULL, 1331},
    {0x1e0606000000ULL, 1440}, {0x1e0606020000ULL, 1520}, {0x1e0800000000ULL, 960}, {0x1e0a02020000ULL, 1401},
    {0x1e0c00000000ULL, 1180}, {0x1e0c04000000ULL, 1330}, {0x1e0e00000000ULL, 1260}, {0x1e0e02020000ULL, 1520},
    {0x1e0e04000000ULL, 1442}, {0x1e0e06000000ULL, 1590}, {0x1e0e06020000ULL, 1695}, {0x1f0000000000ULL, 720},
    {0x1f0101010100ULL, 1176}, {0x1f0102020000ULL, 1400}, {0x1f0202020000ULL, 1146}, {0x1f0204000000ULL, 1290},
    {0x1f0301020000ULL, 1516}, {0x1f0302020000ULL, 1458}, {0x1f0303020000ULL, 1574}, {0x1f0303030000ULL, 1632},
    {0x1f0303030100ULL, 1680}, {0x1f0304000000ULL, 1472}, {0x1f0305010100ULL, 1800}, {0x1f0306020000ULL, 1734},
    {0x1f0404000000ULL, 1096}, {0x1f0505010100ULL, 1620}, {0x1f0506000000ULL, 1626}, {0x1f0604000000ULL, 1388},
    {0x1f0606000000ULL, 1496}, {0x1f0606020000ULL, 1578}, {0x1f0703020000ULL, 1769}, {0x1f0704000000ULL, 1492},
    {0x1f0705010100ULL, 1836}, {0x1f0706000000ULL, 1664}, {0x1f0706020000ULL, 1780}, {0x1f0707000000ULL, 1728},
    {0x1f0707010100ULL, 1920}, {0x1f0707020000ULL, 1856}, {0x1f0707030000ULL, 1960}, {0x1f0707030100ULL, 2040},
    {0x1f0800000000ULL, 996}, {0x1f0901010100ULL, 1500}, {0x1f0a02010000ULL, 1646}, {0x1f0a02020000ULL, 1459},
    {0x1f0b01020000ULL, 1681}, {0x1f0b02020000ULL, 1575}, {0x1f0b03020000ULL, 1762}, {0x1f0b03030000ULL, 1850},
    {0x1f0b03030100ULL, 1926}, {0x1f0c00000000ULL, 1228}, {0x1f0c04000000ULL, 1384}, {0x1f0d01010100ULL, 1620},
    {0x1f0d05010100ULL, 1830}, {0x1f0e00000000ULL, 1302}, {0x1f0e02020000ULL, 1578}, {0x1f0e04000000ULL, 1496},
    {0x1f0e06000000ULL, 1662}, {0x1f0e06020000ULL, 1779}, {0x1f0f00000000ULL, 1344}, {0x1f0f01010100ULL, 1680},
    {0x1f0f01020000ULL, 1764}, {0x1f0f02020000ULL, 1636}, {0x1f0f03020000ULL, 1862}, {0x1f0f03030000ULL, 1960},
    {0x1f0f03030100ULL, 2040}, {0x1f0f04000000ULL, 1552}, {0x1f0f05010100ULL, 1932}, {0x1f0f06000000ULL, 1746},
    {0x1f0f06020000ULL, 1872}, {0x1f0f07000000ULL, 1824}, {0x1f0f07010100ULL, 2040}, {0x1f0f07020000ULL, 1970},
    {0x1f0f07030000ULL, 2098}, {0x1f0f07030100ULL, 2190},
};
// kPosetDual[i]: the class of the transposes of the relations of class i (its dual; computed
// offline from kPosetClasses by the least relabeling of each relation). both_of = the sum of the class plus
// that of its dual. (POSET_VERIFY checks every value against the table of climb4-fast.)
constexpr int kPosetDual[318] = {
    0, 255, 22, 62, 4, 239, 38, 90, 123, 100, 132, 136, 141, 302, 116, 15, 265, 17, 18, 186, 103, 184, 2, 159,
    229, 25, 26, 297, 41, 43, 259, 31, 79, 105, 34, 107, 109, 250, 6, 241, 176, 28, 119, 29, 270, 191, 46, 275,
    48, 49, 53, 197, 121, 50, 277, 55, 199, 57, 279, 201, 152, 313, 3, 257, 214, 65, 114, 127, 143, 304, 162, 288,
    80, 85, 224, 206, 293, 178, 248, 32, 72, 117, 82, 181, 193, 73, 194, 139, 150, 311, 7, 260, 217, 93, 94, 232,
    163, 271, 272, 300, 9, 165, 215, 20, 104, 33, 243, 35, 180, 36, 244, 182, 112, 253, 66, 115, 14, 81, 118, 42,
    274, 52, 196, 8, 261, 170, 218, 67, 185, 129, 145, 306, 10, 166, 262, 290, 11, 219, 167, 87, 226, 12, 263, 68,
    220, 130, 146, 307, 168, 291, 88, 227, 60, 282, 204, 155, 316, 157, 284, 23, 173, 246, 70, 96, 189, 101, 133, 138,
    148, 309, 125, 171, 231, 160, 286, 299, 40, 177, 77, 222, 108, 83, 111, 252, 21, 128, 19, 267, 188, 164, 289, 45,
    192, 84, 86, 225, 122, 51, 278, 56, 200, 59, 281, 203, 154, 315, 75, 207, 268, 294, 210, 242, 212, 249, 64, 102,
    216, 92, 126, 137, 144, 305, 179, 223, 74, 195, 140, 151, 312, 24, 230, 172, 95, 233, 258, 298, 287, 273, 301, 5,
    240, 39, 211, 106, 110, 251, 161, 247, 78, 213, 37, 245, 183, 113, 254, 1, 256, 63, 234, 30, 91, 124, 134, 142,
    303, 16, 266, 187, 208, 295, 44, 97, 98, 237, 120, 47, 276, 54, 198, 58, 280, 202, 153, 314, 158, 285, 174, 236,
    71, 190, 135, 149, 310, 76, 209, 269, 296, 27, 235, 175, 99, 238, 13, 264, 69, 221, 131, 147, 308, 169, 292, 89,
    228, 61, 283, 205, 156, 317,
};
// clang-format on
// The transpose of a relation bit matrix (8 x 8): "b above a" for "a above b".
u64 transpose8(u64 r) {
    u64 t = (r ^ (r >> 7)) & 0x00AA00AA00AA00AAULL;
    r ^= t ^ (t << 7);
    t = (r ^ (r >> 14)) & 0x0000CCCC0000CCCCULL;
    r ^= t ^ (t << 14);
    t = (r ^ (r >> 28)) & 0x00000000F0F0F0F0ULL;
    r ^= t ^ (t << 28);
    return r;
}
// The packed form of a closed relation c (bit 8a + b: a above b), as the relations of WindowRelations:
// bit e (the e-th pair (a, b), a < b, a outer) when a is above b, bit 16 + e when b is above a. The
// transpose of c packs to the two halves exchanged.
constexpr u64 kUpperPairs = 0x0000002030383c3eULL;  // the bits 8a + b, a < b < 6, in the order of e
__attribute__((target("bmi2"))) inline uint32_t pack_relation(u64 c) {
    return uint32_t(_pext_u64(c, kUpperPairs)) | uint32_t(_pext_u64(transpose8(c), kUpperPairs)) << 16;
}
// PosetSums is keyed by the canonical packed relation (the smaller of the packings of a
// relation and of its transpose, which have the same both_of): 65012 keys. The lookup is a displacement
// hash (CHD): the bucket of a key (kBucketBits bits of one hash) holds a displacement d, chosen when the
// table is built so that the keys of the bucket land on distinct free slots of `value` (kSlotBits bits
// of a second hash of key and d). It reads two 16-bit entries (32 KB and 256 KB tables) without a key
// comparison: every query is an acyclic closure, hence a key of the table.
// POSET_VERIFY checks the sums over all 130023 relations.
struct PosetSums {
    static constexpr unsigned kBucketBits = 14, kSlotBits = 17;
    std::vector<uint16_t> displacement, value, one;
    static uint32_t canonical(uint32_t k) { return std::min(k, (k >> 16) | (k << 16)); }
    static unsigned bucket(uint32_t key) {
        return unsigned((u64(key) * 0x9E3779B97F4A7C15ULL) >> (64 - kBucketBits));
    }
    static unsigned slot(uint32_t key, unsigned d) {
        u64 x = (u64(key) << 16 | d) * 0xBF58476D1CE4E5B9ULL;
        x ^= x >> 31;
        x *= 0x94D049BB133111EBULL;
        return unsigned(x >> (64 - kSlotBits));
    }
    // both_of of a canonical packed closed acyclic relation
    __attribute__((always_inline)) int lookup(uint32_t key) const { return value[slot(key, displacement[bucket(key)])]; }
    __attribute__((target("bmi2"))) int both_of(u64 closed) const {
        return lookup(canonical(pack_relation(closed)));
    }
    // Direction-specific expectation for V. The mapper still reads the original
    // sum of the two directions. Canonicalization tells which summand to use.
    __attribute__((target("bmi2"))) int one_of(u64 closed) const {
        const uint32_t packed=pack_relation(closed),key=canonical(packed);
        const unsigned i=slot(key,displacement[bucket(key)]);
        return packed==key?one[i]:value[i]-one[i];
    }
    // The canonical keys with their sums (kPosetDual), then the displacements, the largest buckets first.
    __attribute__((target("bmi2"))) void build() {
        // The classes one of each dual pair (and the self-dual ones): every relabeling of class i, by its
        // canonical key (a relabeling and the transpose of the dual's relabeling share it), once each
        // (seen: an open-addressing set of the keys of class i), with the sum of the class and of its dual.
        std::vector<uint32_t> all_keys;
        std::vector<uint16_t> all_sums, all_one;
        all_keys.reserve(65012);
        all_sums.reserve(65012);all_one.reserve(65012);
        constexpr unsigned kSeen = 2048;
        std::array<uint32_t, kSeen> seen_key{};
        std::array<int, kSeen> seen_class;
        seen_class.fill(-1);
        std::vector<std::array<int, 6>> perms;
        perms.reserve(720);
        std::array<int, 6> p{0, 1, 2, 3, 4, 5};
        do perms.push_back(p);
        while (std::next_permutation(p.begin(), p.end()));
        for (int i = 0; i < 318; i++) {
            if (kPosetDual[i] < i) continue;
            const uint16_t sum = uint16_t(kPosetClasses[i].sum + kPosetClasses[kPosetDual[i]].sum);
            for (const auto& q : perms) {
                u64 r = 0;
                for (u64 x = kPosetClasses[i].relation; x; x &= x - 1) {
                    const int bit = __builtin_ctzll(x);
                    r |= 1ULL << (8 * q[bit >> 3] + q[bit & 7]);
                }
                const uint32_t packed=pack_relation(r),key=canonical(packed);
                unsigned h = unsigned((u64(key) * 0x9E3779B97F4A7C15ULL) >> (64 - 11));
                while (seen_class[h] == i && seen_key[h] != key) h = (h + 1) & (kSeen - 1);
                if (seen_class[h] == i) continue;
                seen_class[h] = i;
                seen_key[h] = key;
                all_keys.push_back(key);
                all_sums.push_back(sum);
                all_one.push_back(uint16_t(packed==key?kPosetClasses[i].sum:kPosetClasses[kPosetDual[i]].sum));
            }
        }
        // the keys grouped by bucket (counting sort), with their sums
        constexpr unsigned kBuckets = 1U << kBucketBits;
        std::vector<int> start(kBuckets + 1, 0);
        for (uint32_t key : all_keys) start[bucket(key) + 1]++;
        for (unsigned b = 0; b < kBuckets; b++) start[b + 1] += start[b];
        std::vector<uint32_t> keys(start[kBuckets]);
        std::vector<uint16_t> sums(start[kBuckets]),ones(start[kBuckets]);
        {
            std::vector<int> at(start.begin(), start.end() - 1);
            for (size_t j = 0; j < all_keys.size(); j++) {
                const int i = at[bucket(all_keys[j])]++;
                keys[i] = all_keys[j];
                sums[i] = all_sums[j];ones[i]=all_one[j];
            }
        }
        // buckets by size (largest first; ties by index): a counting sort by size
        std::vector<int> order(kBuckets);
        {
            std::array<int, 66> by_size{};
            for (unsigned b = 0; b < kBuckets; b++) by_size[std::min(64, start[b + 1] - start[b])]++;
            for (int size = 64, at = 0; size >= 0; size--) {
                const int n = by_size[size];
                by_size[size] = at;
                at += n;
            }
            for (unsigned b = 0; b < kBuckets; b++) order[by_size[std::min(64, start[b + 1] - start[b])]++] = int(b);
        }
        displacement.assign(kBuckets, 0);
        value.assign(1U << kSlotBits, 0);one.assign(1U << kSlotBits,0);
        std::vector<uint8_t> used(1U << kSlotBits, 0);
        std::array<unsigned, 64> slots{};
        for (int b : order) {
            const int lo = start[b], n = start[b + 1] - lo;
            if (!n) break;
            assert(n <= 64);
            for (unsigned d = 0;; d++) {
                assert(d < 65536);
                bool ok = true;
                for (int i = 0; i < n && ok; i++) {
                    slots[i] = slot(keys[lo + i], d);
                    ok = !used[slots[i]];
                    for (int j = 0; j < i && ok; j++) ok = slots[j] != slots[i];
                }
                if (!ok) continue;
                displacement[b] = uint16_t(d);
                for (int i = 0; i < n; i++) {used[slots[i]]=1;value[slots[i]]=sums[lo+i];one[slots[i]]=ones[lo+i];}
                break;
            }
        }
    }
    PosetSums() { build(); }
    static const PosetSums& get() {
        static const PosetSums table;
        return table;
    }
};

int main() {
    const auto& table=PosetSums::get();
    long long checked=0,wrong=0;
    for(int i=0;i<318;++i) {
        std::array<int,6> p{0,1,2,3,4,5};
        do {
            u64 r=0;
            for(u64 z=kPosetClasses[i].relation;z;z&=z-1) {
                int bit=__builtin_ctzll(z);r|=u64(1)<<(8*p[bit/8]+p[bit%8]);
            }
            ++checked;
            wrong+=table.one_of(r)!=kPosetClasses[i].sum;
            wrong+=table.both_of(r)!=kPosetClasses[i].sum+kPosetClasses[kPosetDual[i]].sum;
        } while(std::next_permutation(p.begin(),p.end()));
    }
    std::cout<<"checked "<<checked<<" wrong "<<wrong<<'\n';return wrong?1:0;
}
