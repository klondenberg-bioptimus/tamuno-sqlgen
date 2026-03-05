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

/**
 *
 * Two associated arrays which can be sorted in sync.
 * i.e. one represents an array of keys, the other an array of values.
 * Both arrays can be sorted by keys.
 */
public class ArrayMapSortable implements ISortable {
    private Comparable[] keys;
    private Object[] values;
    
    public ArrayMapSortable(Comparable keys[], Object values[]) {
        this.keys = keys;
        this.values = values;
        if (keys.length!=values.length) throw new IllegalArgumentException("Both arrays must have same size");
    }

    public int length() {
        return keys.length;
    }

    public int compare(int i, int j) {
        return keys[i].compareTo(keys[j]);
    }

    public void swap(int i, int j) {
        Object tmp = keys[i];
        keys[i] = keys[j];
        keys[j] = (Comparable) tmp;
        tmp = values[i];
        values[i] = values[j];
        values[j] = tmp;
    }
}
