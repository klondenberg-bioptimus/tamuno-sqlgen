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

import java.security.MessageDigest;
import java.io.*;
import java.math.BigInteger;
import java.util.Arrays;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Contains an assortment of very useful static methods
 * which get used throughout the Tamuno project.
 * 
 */
public class TamunoUtils {

    public static String loadTextFile(File file) throws IOException {
        return loadTextFile(file, "UTF-8");
    }

    public static String loadTextFile(String filename) throws IOException {
        return loadTextFile(new File(filename), "UTF-8");
    }

    public static String loadTextFile(String filename, String encoding) throws IOException {
        return loadTextFile(new File(filename), encoding);
    }

    /**
     * Loads a Text file into a String, using a given char encoding
     */
    public static String loadTextFile(File file, String encoding) throws IOException {
        if (!file.exists()) {
            return null;
        }
        int size = (int) file.length();
        byte[] buf = new byte[size];
        FileInputStream in = new FileInputStream(file);
        try {
            int rsize = 0;
            int r = 0;
            while (r >= 0 && rsize < file.length()) {
                r = in.read(buf);
                r += rsize;
            }
        } finally {
            in.close();
        }
        String ttext = new String(buf, encoding);
        return ttext;
    }

    /**
     * Upper-cases the first character of the given string.
     * @param s String to capitalize
     * @return capitalized String.
     */
    public static String capitalize(String s) {
        if (s.length() < 1) {
            return s;
        }
        return "" + Character.toUpperCase(s.charAt(0)) + s.substring(1);
    }

    /**
     * Saves a String into a Text file, using a given char encoding
     */
    public static void saveTextFile(File file, String text, String encoding) throws IOException {
        byte[] buf = text.getBytes(encoding);
        FileOutputStream out = new FileOutputStream(file);
        try {
            out.write(buf);
        } finally {
            out.close();
        }
    }

    /**
     * Sets a given bit in a given int array bitfield.
     * @param field array of ints, to be used as a bitfield.
     * @param index bit index
     * @param boolean value to set the given bit to.
     */
    public static final void bitfieldSet(int field[], int index, boolean value) {
        int aidx = index / 32;
        int bidx = index % 32;
        int mask = 1 << bidx;
        if (value) {
            field[aidx] |= mask;
        } else {
            field[aidx] &= ~mask;
        }
    }

    /**
     * Gets a given bit in a given int array bitfield.
     * @param field array of ints, to be used as a bitfield.
     * @param index bit index
     * @return non-zero integer if that bit has been set, zero if it is clear.
     */
    public static final int bitfieldGet(int field[], int index) {
        int aidx = index / 32;
        if (field.length <= aidx) {
            return 0;
        }
        int bidx = index % 32;
        int mask = 1 << bidx;
        return field[aidx] & mask;
    }

    /**
     * Allocates an int array to be used as a bitfield for the given number of bits
     * @param bits bitcount
     * @return allocated int array.
     */
    public static final int[] bitfieldAllocate(int bits) {
        int[] result = new int[1 + (bits / 32)];
        Arrays.fill(result, 0);
        return result;
    }

    /**
     * Allocates an int array bitfield for use as a character class mask
     * the allocated bitfield has all bits set, which belong to bit offsets of
     * all characters in the given String charset.
     * 
     * This can be used for fast charset matchers and scanners.
     * To see if a given char is in a charset, simply use a test like this:
     * 
     * <PRE>
     * int charsetBitfield[] = bitfieldCreateCharSet("ABCDEFG");
     * if (bitfieldGet(charsetBitfield, 'A')!=0) {
     *      System.out.println("The character 'A' is contained in 'ABCDEFG'");
     * }
     * </PRE>
     * @param charset Character set in form of a string.
     * @return allocated and initialized int array
     */
    public static int[] bitfieldCreateCharSet(String charset) {
        char[] set = charset.toCharArray();
        int max = 0;

        for (int i = 0; i < set.length; i++) {
            if (set[i] > max) {
                max = set[i];
            }
        }
        int result[] = bitfieldAllocate(max);
        for (int i = 0; i < set.length; i++) {
            bitfieldSet(result, set[i], true);
        }
        return result;

    }

    /**
     * Returns a standard 128 bit, 32 char hex encoded MD5 of a given String.
     */
    public static final String MD5(String src) throws Exception {
        byte[] digest = MessageDigest.getInstance("MD5").digest(src.getBytes("UTF-8"));
        String md5 = toUnsignedHexStr(digest);
        while (md5.length() < 1) {
            // Nullen voranstellen
            md5 = "0" + md5;
        }
        return md5;
    }
    
    /**
     * Returns a standard 128 bit, 32 char hex encoded MD5 of a given String.
     */
    public static final String MD5(byte data[]) throws Exception {
        byte[] digest = MessageDigest.getInstance("MD5").digest(data);
        String md5 = toUnsignedHexStr(digest);
        while (md5.length() < 1) {
            // Nullen voranstellen
            md5 = "0" + md5;
        }
        return md5;
    }

    /**
     *  Returns a short (8 character) alphanumeric hash based on a 128 bit MD5 calculation.
     */
    public static final String shortAlphanumericHash(String src) throws Exception {
        if (src == null) {
            return null;
        }
        byte[] digest = getMD5Digest().digest(src.getBytes("UTF-8"));
        String shortMD5 = toAlphanumericString(digest);
        while (shortMD5.length() < 8) {
            // Nullen voranstellen
            shortMD5 = "0" + shortMD5;
        }
        return shortMD5.substring(0, 8);
    }

    /**
     * Counts the number of lines in given String
     */
    public static int countLinebreaks(String text) {
        int ct = 0;
        int offset = -1;
        do {
            offset = text.indexOf("\n", offset + 1);
            if (offset < 0) {
                return ct;
            }
            ct++;
        } while (true);
    }

    /**
     * Creates an alphanumeric string, representing the given binary data.
     * Used by shortAlphanumericHash above.
     */
    public static String toAlphanumericString(byte[] data) {
        byte[] absdata = new byte[data.length + 1];
        // Sichergehen, dass es positiv wird.
        absdata[0] = 0;
        System.arraycopy(data, 0, absdata, 1, data.length);
        java.math.BigInteger di = new java.math.BigInteger(absdata);
        return di.toString(35);
    }

    public static String alphaEncode(String str) {
        try {
            return toAlphanumericString(str.getBytes("UTF-8"));
        } catch (UnsupportedEncodingException ex) {
            return null; // Should never happen - UTF-8 must be supported -
        // guaranteed by spec.
        }
    }

    public static String alphaDecode(String str) {
        try {
            java.math.BigInteger i = new BigInteger(str, 35);
            return new String(i.toByteArray(), "UTF-8");
        } catch (UnsupportedEncodingException ex) {
            return null; // Should never happen - UTF-8 must be supported -
        // guaranteed by spec.
        }
    }

    /**
     * Creates an unsigned hexedecimal string, representing the given binary
     * data. Used by MD5 method above.
     */
    public static String toUnsignedHexStr(byte[] data) {
        byte[] absdata = new byte[data.length + 1];
        // Sichergehen, dass es positiv wird.
        absdata[0] = 0;
        System.arraycopy(data, 0, absdata, 1, data.length);
        java.math.BigInteger di = new java.math.BigInteger(absdata);
        return di.toString(16);
    }

    public static String loadTextFromClassloader(String fname, ClassLoader cls, String encoding) throws IOException {
        BufferedReader brin = null;
        StringBuilder sb = new StringBuilder();
        try {
            InputStream is = cls.getResourceAsStream(fname);
            InputStreamReader in = new InputStreamReader(is, encoding);

            brin = new BufferedReader(in);

            int c = brin.read();
            while (c != -1) {
                sb.append((char) c);
                c = brin.read();
            }
        } finally {
            try {
                brin.close();
            } catch (Exception ex) {
            // Swallowed.
            }
        }
        return sb.toString();
    }

    /**
     * Returns MessageDigest object for MD5 Algorithm.
     */
    private static MessageDigest getMD5Digest() throws Exception {
        return MessageDigest.getInstance("MD5");
    }

    /**
     * <p>Returns an upper case hexadecimal <code>String</code> for the given
     * character.</p>
     *
     * @param ch The character to convert.
     * @return An upper case hexadecimal <code>String</code>
     */
    public static String hex(char ch) {
        return Integer.toHexString(ch).toUpperCase();
    }

    private static boolean doEscapeJavaChar(char c) {
        switch (c) {
            case 'ü':
            case 'Ü':
            case 'Ö':
            case 'ö':
            case 'ä':
            case 'Ä':
            case 'ß':
            case '€':
                return false;
        }
        return true;
    }

    /**
     * Escapes an arbitrary String to be included in Java source code.
     * Used in the Tamuno Code generator.
     */
    public static String escapeJavaString(String str) {
        if (str == null) {
            return null;
        }
        StringBuilder out = new StringBuilder();
        int sz;
        sz = str.length();
        for (int i = 0; i < sz; i++) {
            char ch = str.charAt(i);

            // handle unicode
            if (ch > 0xfff) {
                if (doEscapeJavaChar(ch)) {
                    out.append("\\u" + hex(ch));
                } else {
                    out.append(ch);
                }
            } else if (ch > 0xff) {
                if (doEscapeJavaChar(ch)) {
                    out.append("\\u0" + hex(ch));
                } else {
                    out.append(ch);
                }
            } else if (ch > 0x7f) {
                if (doEscapeJavaChar(ch)) {
                    out.append("\\u00" + hex(ch));
                } else {
                    out.append(ch);
                }
            } else if (ch < 32) {
                switch (ch) {
                    case '\b':
                        out.append('\\');
                        out.append('b');
                        break;
                    case '\n':
                        out.append('\\');
                        out.append('n');
                        break;
                    case '\t':
                        out.append('\\');
                        out.append('t');
                        break;
                    case '\f':
                        out.append('\\');
                        out.append('f');
                        break;
                    case '\r':
                        out.append('\\');
                        out.append('r');
                        break;
                    default:
                        if (doEscapeJavaChar(ch)) {
                            if (ch > 0xf) {
                                out.append("\\u00" + hex(ch));
                            } else {
                                out.append("\\u000" + hex(ch));
                            }
                        } else {
                            out.append(ch);
                        }
                        break;
                }
            } else {
                switch (ch) {
                    case '\'':
                        out.append('\'');
                        break;
                    case '"':
                        out.append('\\');
                        out.append('"');
                        break;
                    case '\\':
                        out.append('\\');
                        out.append('\\');
                        break;
                    default:
                        out.append(ch);
                        break;
                }
            }
        }
        return out.toString();
    }

    /**
     * Unescapes a given java source String, replacing escape sequences
     * with the correct characters. Used in the Java Parser to get
     * the real values of String literals.
     */
    public static String unescapeJavaString(String str) {
        if (str == null) {
            return null;
        }
        StringBuilder out = new StringBuilder();
        int sz = str.length();
        StringBuffer unicode = new StringBuffer(4);
        boolean hadSlash = false;
        boolean inUnicode = false;
        for (int i = 0; i < sz; i++) {
            char ch = str.charAt(i);
            if (inUnicode) {
                // if in unicode, then we're reading unicode
                // values in somehow
                unicode.append(ch);
                if (unicode.length() == 4) {
                    // unicode now contains the four hex digits
                    // which represents our unicode character
                    try {
                        int value = Integer.parseInt(unicode.toString(), 16);
                        out.append((char) value);
                        unicode.setLength(0);
                        inUnicode = false;
                        hadSlash = false;
                    } catch (NumberFormatException nfe) {
                        throw new RuntimeException("Unable to parse unicode value: " + unicode, nfe);
                    }
                }
                continue;
            }
            if (hadSlash) {
                // handle an escaped value
                hadSlash = false;
                switch (ch) {
                    case '\\':
                        out.append('\\');
                        break;
                    case '\'':
                        out.append('\'');
                        break;
                    case '\"':
                        out.append('"');
                        break;
                    case 'r':
                        out.append('\r');
                        break;
                    case 'f':
                        out.append('\f');
                        break;
                    case 't':
                        out.append('\t');
                        break;
                    case 'n':
                        out.append('\n');
                        break;
                    case 'b':
                        out.append('\b');
                        break;
                    case 'u': {
                        // uh-oh, we're in unicode country....
                        inUnicode = true;
                        break;
                    }
                    default:
                        out.append(ch);
                        break;
                }
                continue;
            } else if (ch == '\\') {
                hadSlash = true;
                continue;
            }
            out.append(ch);
        }
        if (hadSlash) {
            // then we're in the weird case of a \ at the end of the
            // string, let's output it anyway.
            out.append('\\');
        }
        return out.toString();
    }

    /** 
     *  Determines minimum indentation Level of a block of java code,
     *  and tries to remove that prefix from every line.
     *  Then prefixes every line with minIndent String.
     */
    public static String indentBlock(String codeBlock, String minIndent) {
        minIndent = minIndent.replaceAll("\t", "    ");
        String lines[] = codeBlock.split("\n");
        Pattern whitespacePrefix = Pattern.compile("^([ \t]*)(.*)$", Pattern.MULTILINE);
        Matcher m = whitespacePrefix.matcher(codeBlock);
        String linePrefix[] = new String[lines.length];
        String lineContent[] = new String[lines.length];
        int i = 0;
        String normalPrefix = null;
        String shortestNormalPrefix = "                                                                                                                        ";
        while (m.find()) {
            linePrefix[i] = m.group(1);
            lineContent[i] = m.group(2);
            normalPrefix = linePrefix[i].replaceAll("\t", "    ");
            if (normalPrefix.length() < shortestNormalPrefix.length()) {
                shortestNormalPrefix = normalPrefix;
            }
            i++;
        }
        assert (i == lines.length);
        StringBuilder result = new StringBuilder();
        for (i = 0; i < lines.length; i++) {
            normalPrefix = linePrefix[i].replaceAll("\t", "    ");
            normalPrefix = normalPrefix.substring(shortestNormalPrefix.length());
            String prefix = minIndent + normalPrefix;
            prefix = prefix.replaceAll("    ", "\t");
            result.append(prefix);
            result.append(lineContent[i]);
            result.append("\n");
        }
        return result.toString();
    }

    /**
     * returns a String consisting of a given String repeated severeal times.
     */
    public static String repeatString(int count, String str) {
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < count; i++) {
            result.append(str);
        }
        return result.toString();
    }


    public static String toHTTPQueryString(String keys[], String values[]) {
        // Sort them in place..
        ArrayMapSortable sortable = new ArrayMapSortable(keys, keys);
        if (!Sorter.checkSort(sortable)) {
            Sorter.heapsort(sortable);
        }
        StringBuilder qs = new StringBuilder();
        int len = keys.length;
        try {
            for (int i = 0; i < len; i++) {

                if (values.length <= i) {
                    break;
                }
                if (values[i] == null) {
                    continue;
                }
                if (i > 0) {
                    qs.append("&");
                }
                qs.append(keys[i]);
                qs.append("=");
                qs.append(java.net.URLEncoder.encode(values[i], "UTF-8"));

            }
        } catch (UnsupportedEncodingException ex) {
            ex.printStackTrace();
            // Can't happen, UTF-8 must be supported by Java specification.
            return null;
        }
        return qs.toString();
    }

    public static void recursiveDelete(File f, int maxDepth) throws Exception {
        if (maxDepth == 0) {
            throw new Exception("Max recursion level reached");
        }
        if (f.isDirectory()) {
            File children[] = f.listFiles();
            for (File cf : children) {
                recursiveDelete(cf, maxDepth - 1);
            }
        }
        f.delete();
    }

    public static String htmlentities(String s) {
        int len = s.length();
        StringBuffer sb = new StringBuffer(len * 5 / 4);

        for (int i = 0; i < len; i++) {
            char c = s.charAt(i);
            String elem = htmlchars[c & 0xff];

            sb.append(elem == null ? "" + c : elem);
        }
        return sb.toString();
    }
    private static String htmlchars[] = new String[256];

    static {
        String entry[] = {
            "nbsp", "iexcl", "cent", "pound", "curren", "yen", "brvbar",
            "sect", "uml", "copy", "ordf", "laquo", "not", "shy", "reg",
            "macr", "deg", "plusmn", "sup2", "sup3", "acute", "micro",
            "para", "middot", "cedil", "sup1", "ordm", "raquo", "frac14",
            "frac12", "frac34", "iquest",
            "Agrave", "Aacute", "Acirc", "Atilde", "Auml", "Aring", "AElig",
            "CCedil", "Egrave", "Eacute", "Ecirc", "Euml", "Igrave", "Iacute",
            "Icirc", "Iuml", "ETH", "Ntilde", "Ograve", "Oacute", "Ocirc",
            "Otilde", "Ouml", "times", "Oslash", "Ugrave", "Uacute", "Ucirc",
            "Uuml", "Yacute", "THORN", "szlig",
            "agrave", "aacute", "acirc", "atilde", "auml", "aring", "aelig",
            "ccedil", "egrave", "eacute", "ecirc", "euml", "igrave", "iacute",
            "icirc", "iuml", "eth", "ntilde", "ograve", "oacute", "ocirc",
            "otilde", "ouml", "divid", "oslash", "ugrave", "uacute", "ucirc",
            "uuml", "yacute", "thorn", "yuml"
        };

        htmlchars['&'] = "&";
        htmlchars['<'] = "<";
        htmlchars['>'] = ">";

        for (int c = '\u00A0',  i = 0; c <= '\u00FF'; c++, i++) {
            htmlchars[c] = "&" + entry[i] + ";";
        }

        for (int c = '\u0083',  i = 131; c <= '\u009f'; c++, i++) {
            htmlchars[c] = "&#" + i + ";";
        }

        htmlchars['\u0088'] = htmlchars['\u008D'] = htmlchars['\u008E'] = null;
        htmlchars['\u008F'] = htmlchars['\u0090'] = htmlchars['\u0098'] = null;
        htmlchars['\u009D'] = null;
    }
}
