"""組移動の候補表に、同じ組での色反転も含める。"""
def unified(t):
    old='''        const uint32_t allowed = ((1U << 30)-1) & ~((1U << ea) | (1U << (ea+15)));'''
    new='''        // A singleton group may only flip its own window. Other groups may send the
        // window to any edge. Exclude only the exact no-op (same edge and old color).
        const uint32_t destinations=counts[ea]>1 ? (1U<<30)-1 : (1U<<ea)|(1U<<(ea+15));
        const uint32_t allowed=destinations & ~(1U<<(ea+15*int(pol>>a&1)));'''
    assert old in t;t=t.replace(old,new,1)
    t=t.replace('''        } else {  // window a to another pair
            if (counts[ea] < 2) return false;''','''        } else {  // jointly choose an edge and color, including a same-edge flip
            if (counts[ea] < 2 && selected.size()!=unsigned(need)) return false;''',1)
    old='''            if (ea == eb) return false;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
            if (new_color >= 0) pol = (pol & ~(1ULL << a)) | (u64(new_color) << a);
            else if (rng.next() & 1) pol ^= 1ULL << a;'''
    new='''            oldb = mask[eb];
            if (ea==eb) {
                if (new_color<0) return false;
                kind=0; // Use the usual flip key and unchanged counts on acceptance.
            } else {
                mask[ea] ^= 1ULL << a;
                mask[eb] |= 1ULL << a;
                transfer=eb;
            }
            if (new_color >= 0) pol = (pol & ~(1ULL << a)) | (u64(new_color) << a);
            else if (rng.next() & 1) pol ^= 1ULL << a;'''
    assert old in t;t=t.replace(old,new,1)
    return t
