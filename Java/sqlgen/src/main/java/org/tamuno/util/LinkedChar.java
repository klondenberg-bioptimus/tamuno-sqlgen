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
 * Character in a doubly linked list - is capable of carrying payload to identify it's source.
 * @see LinkedString
 */
public class LinkedChar<T> {
    LinkedChar<T> prev = null;
    LinkedChar<T> next = null;
    T payload = null;
    char character;
    int origIndex = -1;

    LinkedChar(char character, T payload, LinkedChar<T> prev, LinkedChar<T> next) {
        this.payload = payload;
        this.next = next;
        this.prev = prev;
        this.character = character;
    }
    
    public LinkedChar(char character, T payload) {
        this(character, payload, null, null);
    }
    
    public void insertBefore(LinkedString<T> str) {
        LinkedString<T> newStr = new LinkedString<T>(str);
        newStr.firstChar.prev = this.prev;
        if (this.prev!=null) {
            // This looks funny, but it can actually happen that this.prev.next
            // is not this (if this char has been removed)
            LinkedChar pn = this.prev.next;
            this.prev.next = newStr.firstChar;
            newStr.lastChar.next = pn;
            if (pn!=null) {
                pn.prev = newStr.lastChar;
            }
        } else if (this.next!=null) {
            newStr.lastChar.next = this.next.prev;
            if (this.next.prev==null) { // We have been removed from the start of a string.
                newStr.lastChar.next = this.next;
                this.next.prev = newStr.lastChar;
            }            
        } else {
            newStr.lastChar.next = this;
        }
        if (newStr.lastChar.next!=null) {
            newStr.lastChar.next.prev = newStr.lastChar;
        }
        this.prev = newStr.lastChar;
    }
    
    public void insertAfter(LinkedString<T> str) {
        LinkedString newStr = new LinkedString(str);
        newStr.lastChar.next = this.next;
        if (this.next!=null) {
            // This looks funny, but it can actually happen that this.next.prev
            // is not this (if this char has been removed)
            LinkedChar pn = this.next.prev;
            this.next.prev = newStr.lastChar;
            newStr.firstChar.prev = pn;
            if (pn!=null) {
                pn.next = newStr.firstChar;
            }
        } else if (this.prev!=null) {
            newStr.firstChar.prev = this.prev.next;
            if (this.prev.next==null) { // We have been removed from the start of a string.
                newStr.firstChar.prev = this.prev;
                this.prev.next = newStr.firstChar;
            }  
        } else {
            newStr.firstChar.prev = this;
        }
        if (newStr.firstChar.prev!=null) {
            newStr.firstChar.prev.next = newStr.firstChar;
        }
        this.next = newStr.firstChar;
    }

    public char getCharacter() {
        return character;
    }

    public LinkedChar<T> getNext() {
        return next;
    }

    public T getPayload() {
        return payload;
    }

    public LinkedChar<T> getPrev() {
        return prev;
    }
    
    @Override
    public String toString() {
        return "" + character + "("+origIndex+")";
    }
    
    
}
