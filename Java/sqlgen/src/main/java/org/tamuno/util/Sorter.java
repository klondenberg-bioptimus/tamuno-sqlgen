/*

 Tamuno Framework 

Copyright: Kai Londenberg, 2007, Germany.

This software is made available as is, without any explicit
or implied warranties, to the extent permitted by law.

The Tamuno Framework is licensed under the Apache Public License V2.0
see LICENSE.txt

The TamunoFramework contains external Open Source Libraries, to
which the original Author has no copyright, and which are
available under their own licensing terms.

*/

package org.tamuno.util;


public class Sorter {
    
    /**
     * Heap Sort any Object which implements the ISortable Interface.
     */
    public static ISortable heapsort(ISortable s) {
        phase1(s);  // build initial heap
        phase2(s);  // sort the sortable given the heap
        return s;   // return the Sortable for convenience
    }
    
    public static boolean checkSort(ISortable s) {
        int max = s.length()-1;
        for (int i=0;i<max;i++) {
            if (s.compare(i, i+1)>0) {
                return false;
            }
        }
        return true;
    }
    
    
    private static void heapify(ISortable s, int p, int n) {
        for (int r, l= (p<<1)+1; l < n; p= l, l= (p<<1)+1) {
            // l is the maximum of l and r, the two subnodes of p
            if ((r= l+1) < n && s.compare(l, r) < 0) l= r;
            // check if parent p is less than maximum l
            if (s.compare(p, l) < 0) s.swap(p, l);
            else break;
            
        }
        
    }
    
    private static void phase1(ISortable s) {
        // heapify all the non-leaf nodes
        for (int n= s.length(), p= n/2; p >= 0; p--)
            heapify(s, p, n);
    }
    
    private static void phase2(ISortable s) {
        for (int n= s.length(); --n > 0; ) {
            s.swap(0, n);     // put the root element in its place
            heapify(s, 0, n);   // and restore the heap again
        }
    }
    
}
