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
 * String implementation, which allows to modify the string. 
 * characters are implemented as a linked list, and also available in an
 * original array. So it is possible to efficiently modify the string (insertions deletions etc.)
 * and still keep track of where a given original character went.
 * Imporant to apply a set of edit operations onto a string, when the edit operations refer to
 * original offsets, yet these offsets can be modified by the same edit operations.
 * <br><br>
 * This class implements CharSequence, Appendable and Comparable, and as such can be used
 * in most cases when a real string can be used.
 * 
 * also, it implements toString() and toOriginal() String methods.
 * Every character can carry an object reference as a payload. The type of this
 * payload gets determined by T.
 * <br><br>
 * A JUnit Test case for this class is available in org.tamuno.util.LinkedStringTest
 * 
 * 
 */
public class LinkedString<T> implements CharSequence, Appendable, Comparable {

    public static int defaultMaxLength = 1024*1024*16;
    
    LinkedChar<T> firstChar = null;
    LinkedChar<T> lastChar = null;
    LinkedChar<T> originalArray[] = null;
    T defaultPayload;
    private String cachedString;
    
    /*
     * Construct Linked String with the given original String, and the given payload.
     */     
    public LinkedString(String src, T defaultPayload) {
        this.defaultPayload = defaultPayload;
        this.originalArray = (LinkedChar<T>[]) new LinkedChar[src.length()];
        for (int i=0;i<originalArray.length;i++) {
            originalArray[i] = new LinkedChar(src.charAt(i), defaultPayload, null, null);
        }
        reset();
    }
    
    private void modified() {
        cachedString = null;
    }
    
    /**
     * Tests whether the original character at the given index is still present in this string.
     */
    public int indexOfOriginalChar(int index) {
        LinkedChar<T> orig = originalArray[index];
        LinkedChar c = firstChar;
        int p=0;
        while (c!=null) {
            if (c==orig) {
                return p;
            }
            c = c.next;
            p++;
        }
        return -1;
    }
    
    /**
     * Creates a deep copy of a given linked string, which transforms the current form of
     * that linked string to the current original value.
     * @param src
     * @param maxLength
     */
    public LinkedString(LinkedString<T> src, int maxLength) {
        this.defaultPayload = src.defaultPayload;
        this.originalArray = (LinkedChar<T>[]) new LinkedChar[src.length(maxLength)];
        if (this.originalArray.length>0) {
            LinkedChar c = src.firstChar;        
            LinkedChar cchar = new LinkedChar(c.character, c.payload, null, null);
            firstChar = cchar;
            originalArray[0] = firstChar;

            lastChar = cchar;
            c = c.next;
            int breakLoopAt = maxLength-1;
            int pos = 1;

            while (c!=null) {
                LinkedChar nextchar = new LinkedChar(c.character, c.payload, cchar, null);
                cchar.next = nextchar;
                originalArray[pos++] = nextchar;
                cchar = nextchar;
                if (c==src.lastChar) {
                    break;
                }
                c = c.next;                        
                if (breakLoopAt--==0) {
                    throw new RuntimeException("Possible loop in LinkedString - breaking at " + (maxLength - breakLoopAt));
                }

            }
            if (cchar!=null) {
                lastChar = cchar;
            }
        }
        reset();
        
    }
    
    /**
     * Creates a deep copy of a given linked string, which transforms the current form of
     * that linked string to the current original value.
     * @param src
     * @param maxLength
     */
    public LinkedString(LinkedString<T> src, int maxLength, int startOffset, int endOffset) {
        this.defaultPayload = src.defaultPayload;
        this.originalArray = (LinkedChar<T>[]) new LinkedChar[endOffset-startOffset];
        if (this.originalArray.length>0) {
            LinkedChar start = src.getCharFromStart(startOffset);
            LinkedChar stop = src.getCharFromStart(endOffset-1);
            LinkedChar c = start;        
            LinkedChar cchar = new LinkedChar(c.character, c.payload, null, null);
            firstChar = cchar;
            originalArray[0] = firstChar;

            lastChar = cchar;
            c = c.next;
            int breakLoopAt = maxLength-1;
            int pos = 1;

            while (c!=null) {
                LinkedChar nextchar = new LinkedChar(c.character, c.payload, cchar, null);
                cchar.next = nextchar;
                originalArray[pos++] = nextchar;
                cchar = nextchar;
                if (c==stop) {
                    break;
                }
                c = c.next;                        
                if (breakLoopAt--==0) {
                    throw new RuntimeException("Possible loop in LinkedString - breaking at " + (maxLength - breakLoopAt));
                }

            }
            if (cchar!=null) {
                lastChar = cchar;
            }
        }
        reset();
        
    }
    
    public LinkedString(LinkedString<T> src) {
        this(src, defaultMaxLength);
    }
    
    public void reset() {
        modified();
        for (int i=0;i<originalArray.length-1;i++) {
            originalArray[i].origIndex = i;
        }
        for (int i=0;i<originalArray.length-1;i++) {
            originalArray[i].next = originalArray[i+1];
        }
        for (int i=1;i<originalArray.length;i++) {
            originalArray[i].prev = originalArray[i-1];
        }
        if (originalArray.length>0) {
            firstChar = originalArray[0];
            lastChar = originalArray[originalArray.length-1];
        }
    }
    
    public String toString(int breakLoopAt) {
        if (cachedString!=null) {
            return cachedString;
        }
        StringBuilder sb = new StringBuilder();
        
        LinkedChar c = firstChar;
        while (c!=null) {
            if (breakLoopAt--==0) {
                throw new RuntimeException("Possible loop in LinkedString - breaking at " + sb.length()+":"+sb.substring(0,40)+"[...]"+sb.substring(sb.length()-40));
            }
            sb.append(c.character);
            if (c==lastChar) {
                break;
            }
            c = c.next;
        }
        cachedString = sb.toString();
        return cachedString;
    }
    
    public int length(int breakAtSize) {
        int result = 0;
        LinkedChar c = firstChar;
        while (c!=null) {
            if (breakAtSize--==0) {
                throw new RuntimeException("Possible loop in LinkedString - breaking at " +result);
            }
            result++;
            if (c==lastChar) {
                break;
            }
            c = c.next;
        }
        return result;
    }
    
    public int length() {
        return this.length(defaultMaxLength);
    }
    
    public int originalLength() {
        return this.originalArray.length;
    }
    
    @Override
    public String toString() {
        return this.toString(defaultMaxLength);
    }
    
    public String toOriginalString() {
        StringBuilder sb = new StringBuilder();
        for (int i=0;i<originalArray.length;i++) {
            sb.append(originalArray[i].character);
        }
        return sb.toString();
    }
    
    public LinkedChar getCharFromStart(int pos) {
        LinkedChar c = firstChar;
        for (int i=1;i<=pos;i++) {
            if (c==null) {
                return null;
            }
            c = c.next;
        }
        return c;
    }
    
    public LinkedChar getCharFromEnd(int pos) {
        LinkedChar c = lastChar;
        for (int i=1;i<=pos;i++) {
            if (c==null) {
                return null;
            }
            c = c.prev;
        }
        return c;
    }
    
    public LinkedChar getOriginalCharAt(int pos) {
        if (pos>=this.originalArray.length) {
            return null;
        }
        return this.originalArray[pos];
    }
    
    public LinkedString substring(int startOffset, int endOffset) {
        return new LinkedString<T>(this, defaultMaxLength, startOffset, endOffset);
    }

    public char charAt(int index) {
        return this.getCharFromStart(index).getCharacter();
    }

    public CharSequence subSequence(int start, int end) {
        return this.substring(start,end);
    }
    
    public LinkedString<T> append(LinkedString ls) {
        modified();
        if (this.lastChar == null) { // We are an empty String, until now ..
            LinkedString st = new LinkedString(ls);
            this.firstChar = st.firstChar;
            this.lastChar = st.lastChar;
            return this;
        }
        insertAfter(this.lastChar, ls);
        return this;
    }

    public Appendable append(CharSequence csq) {
        if (this.lastChar == null) { // We are an empty String, until now ..
            LinkedString st = new LinkedString(csq.toString(), this.defaultPayload);
            this.firstChar = st.firstChar;
            this.lastChar = st.lastChar;
            return this;
        }
        return append(new LinkedString(csq.toString(), this.defaultPayload));
    }

    public Appendable append(CharSequence csq, int start, int end) {
        return append(csq.subSequence(start, end));
    }
    
    public void insertAfter( LinkedChar after, LinkedString str) {
        modified();
        if ((this.lastChar == null) && (after==null)) { // We are an empty String, until now ..
            LinkedString st = new LinkedString(str);
            this.firstChar = st.firstChar;
            this.lastChar = st.lastChar;
            return;
        } else if (after.prev==lastChar) { // Character after current end, which has been removed
            after = lastChar;
        } else if (after.next==firstChar) { // Character after current end, which has been removed.
            insertBefore(firstChar, str);
            return;
        }
        after.insertAfter(str);
        if (after==this.lastChar) {
            int off = str.length();
            for (int i=0;i<off;i++) {
                lastChar = lastChar.next;
            }
        }
    }
    
    public void insertBefore( LinkedChar before, LinkedString str) {
        modified();
        if ((this.firstChar == null) && (before==null)) { // We are an empty String, until now ..
            LinkedString st = new LinkedString(str);
            this.firstChar = st.firstChar;
            this.lastChar = st.lastChar;
            return;
        } else if (before.next==firstChar) { // Character before current start, which has been removed
            before = firstChar;
        } else if (before.prev==lastChar) { // Character after current end, which has been removed.
            insertAfter(lastChar, str);
            return;
        }
        before.insertBefore(str);
        if (before==this.firstChar)  {
            int off = str.length();
            for (int i=0;i<off;i++) {
                firstChar = firstChar.prev;
            }
        }
    }

    public Appendable append(char c) {
        modified();
        if (lastChar!=null) {
            LinkedChar t = lastChar.next;
            lastChar.next = new LinkedChar(c, this.defaultPayload);
            lastChar.next.prev = lastChar;
            lastChar = lastChar.next;
            lastChar.next = t;
        } else {
            firstChar = new LinkedChar(c, this.defaultPayload);
            lastChar = new LinkedChar(c, this.defaultPayload);
        }
        return this;
    }
    
    public void remove(LinkedChar start, LinkedChar afterEnd) {
        modified();
        LinkedChar end = null;
        if (afterEnd!=null) {
            end = afterEnd.prev;
        }
        
        if (start==this.firstChar) {
            if (end==null) {
                firstChar=null;
                lastChar = null;
                return;
            }
            firstChar = end.next;
            firstChar.prev = null;
        } else if (start==null) {
            if (end==null) {
                firstChar=null;
                lastChar = null;
                return;
            }
            firstChar = end.next;
        } else if (start.prev!=null) {
            if (end!=null) {
                start.prev.next = end.next;
            } else {
                start.prev.next = null;
            }
        }
        
        if (end==this.lastChar) {
            lastChar = start.prev;           
        } else if (end==null) {
            // We assert start!=null
            lastChar = start.prev;
        } else if (end.next!=null) {
            if (start!=null) {
                end.next.prev = start.prev;
            } else {
                end.next.prev = null;
            }
        }
        LinkedChar tmpNext = start.next;
        LinkedChar current = start;
        // Now we re-link the LinkedChars inbetween, so that insertions originating from
        // deleted characters (which may still be reachable through the original array)
        // are inserted at the correct place.
        while ((current!=null) && ((end==null) || (current!=end.next))) {
            tmpNext = current.next;
            if (end!=null) {
                current.next = end.next;
            } else {
                current.next = null;
            }
            if (start!=null) {
                current.prev = start.prev;
            } else {
                current.prev = null;
            }
            current = tmpNext;
        }
        
    }
    
    public void remove(int from, int to) {
        remove(this.getCharFromStart(from), this.getCharFromStart(to));
    }
    
    public void removeOriginalRange(int from, int to) {
        remove(this.getOriginalCharAt(from), this.getOriginalCharAt(to));
    }
    
    public LinkedChar<T>[] getOriginalCharArray() {
        return (LinkedChar<T>[]) this.originalArray.clone();
    }
    
    public LinkedChar<T>[] getCharArray() {
        LinkedChar<T>[] result = (LinkedChar<T>[]) new LinkedChar[this.length()];
        LinkedChar current = firstChar;
        int i=0;
        while (current!=null) {
            result[i++] = current;
            if (current==lastChar) break;
            current = current.next;
        }
        return result;
    }
    
    public int compareTo(Object o) {
        return this.toString().compareTo(o.toString());
    }
    
    public boolean equals(Object o) {
        return this.toString().equals(o);
    }
    
    public boolean equalsIgnoreCase(String s) {
        return this.toString().equalsIgnoreCase(s);
        
    }
    
    public boolean startsWith(String s) {
        return this.toString().startsWith(s);
    }
    
    public boolean endsWith(String s) {
        return this.toString().endsWith(s);
    }
    
    public int hashCode() {
        return this.toString().hashCode();
    }
    

}
