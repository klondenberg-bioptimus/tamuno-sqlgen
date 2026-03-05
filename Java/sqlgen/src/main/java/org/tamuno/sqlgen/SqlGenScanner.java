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

package org.tamuno.sqlgen;
import java.util.ArrayList;
import static org.tamuno.sqlgen.SQLGenTokenType.*;
import java.util.BitSet;
import java.util.Stack;
import org.tamuno.util.TamunoUtils;

/**
 * Fast scanner, tokenizes a given SQLGenerator Source into
 * Tokens manageable gby the SQLGenParser
 *  
 */
public class SqlGenScanner {
    private String str;
    
    private static final char openBracket = '[';
    private static final char closeBracket = ']';
    private static final char requiredOpenBracket = '{';
    private static final char requiredCloseBracket = '}';
    
    private static final char escapedVar = '$';
    private static final char literalVar = '#';
    private static final char optionVar = '?';
    private static final char targetVar = '@';
    private static final char typeSeparator = ':';
    
    private static final int[] stopLiteralSet = TamunoUtils.bitfieldCreateCharSet("" + openBracket + closeBracket + requiredOpenBracket + requiredCloseBracket + escapedVar + literalVar + targetVar + optionVar + '"' + "'" + '\\');
    private static final int[] identifierSet = TamunoUtils.bitfieldCreateCharSet("abcdefghijklmnopqrstuvwxyzABCDERFGHIJKLMNOPQRSTUVWXYZ0123456789_");
        
    private SQLGenTokenType currentType = LITERAL;
    private boolean inQuote = false;
    private char quoteChar;
    
    
    private int pos = 0;
    private int tokenStart = 0;
    private char chars[];
    
    public synchronized ArrayList<SQLGenToken> scanString(String str) throws SQLGenParseException {
        this.str = str;
        pos = 0;
        currentType = LITERAL;
        this.chars = str.toCharArray();
        ArrayList<SQLGenToken> result = new ArrayList<SQLGenToken>();
        int len = chars.length;
        Stack<SQLGenTokenType> bracketStack = new Stack<SQLGenTokenType>();
        StringBuilder currentTokenText = new StringBuilder();
        loop:
        while (pos<len) {
                    int npos = nextIndexOf(stopLiteralSet);
                    if (npos==-1) {
                        currentTokenText.append(str.substring(pos));
                        result.add(new SQLGenToken(currentType, currentTokenText.toString()));
                        currentTokenText.setLength(0);
                        break loop;
                    }
                    currentTokenText.append(str.substring(pos, npos));
                    // Skip character following escape char
                    if (chars[npos]=='\\') {
                        pos = npos+2;
                        if (inQuote) { // We preserve escape chars in quotes.
                            currentTokenText.append('\\');
                        }
                        
                        if (len>(npos+1)) {
                            currentTokenText.append(chars[npos+1]);
                        }
                        continue loop;
                    }
                    if (inQuote) {
                        // Tolerate everything until end of quote, respecting escapes (see above)
                        if (chars[npos]==quoteChar) {
                            inQuote = false;
                        }
                        currentTokenText.append(chars[npos]);
                        pos = npos+1;
                        continue loop;
                    }
                    // Start of quote.
                    if ((chars[npos]=='\'') || (chars[npos]=='"')) {
                        inQuote = true;
                        quoteChar = chars[npos];
                        currentTokenText.append(quoteChar);
                        pos = npos+1;
                        continue loop;
                    }
                    result.add(new SQLGenToken(currentType, currentTokenText.toString()));
                    currentTokenText.setLength(0);
                    switch (chars[npos]) {
                        case openBracket:
                            result.add(new SQLGenToken(SQLGenTokenType.OPEN_BRACKET, ""+openBracket));
                            bracketStack.push(OPEN_BRACKET);
                            pos = npos+1;
                            continue loop;
                        case closeBracket:
                            result.add(new SQLGenToken(SQLGenTokenType.CLOSE_BRACKET, ""+closeBracket));
                            if (bracketStack.empty() || (bracketStack.pop()!=OPEN_BRACKET)) {
                                throw new SQLGenParseException(npos, "Mismatched closing bracket");
                            }
                            pos = npos+1;
                            continue loop;
                        case requiredOpenBracket:
                            result.add(new SQLGenToken(SQLGenTokenType.REQUIRED_OPEN_BRACKET, ""+requiredOpenBracket));
                            bracketStack.push(REQUIRED_OPEN_BRACKET);
                            pos = npos+1;
                            continue loop;
                        case requiredCloseBracket:
                            result.add(new SQLGenToken(SQLGenTokenType.REQUIRED_CLOSE_BRACKET, ""+requiredCloseBracket));
                            if (bracketStack.empty() || (bracketStack.pop()!=REQUIRED_OPEN_BRACKET)) {
                                throw new SQLGenParseException(npos, "Mismatched closing bracket");
                            }
                            pos = npos+1;
                            continue loop;
                        case escapedVar:
                            currentType = SQLGenTokenType.ESCAPED_VAR; 
                            break;
                        case literalVar:
                            currentType = SQLGenTokenType.LITERAL_VAR; 
                            break;
                        case targetVar:
                            currentType = SQLGenTokenType.TARGET_VAR;
                            break;
                        case optionVar:
                            currentType = SQLGenTokenType.OPTION_VAR;
                            break;
                    }
                    int cpos = pos;
                    pos = npos+1;
                    // we have a variable, so we are going to parse it.
                    String identifier = consumeIdentifier();
                    String vartype = null;
                    
                    if (pos<chars.length) {
                        if (chars[pos]==typeSeparator) {
                            pos++;
                            vartype = consumeIdentifier();
                        }
                    }
                    if (identifier==null) {
                        throw new SQLGenParseException(cpos, "Missing identifier for variable");
                    }
                    result.add(new SQLGenToken(currentType, identifier, vartype));
                    currentType = SQLGenTokenType.LITERAL;
        }
        if (!bracketStack.empty()) {
            throw new SQLGenParseException(str.length(), ""+ bracketStack.size() + " unclosed bracket(s) in "+ str);
        }
        return result;
    }
    
    
    
    private String consumeIdentifier() {
        int npos = endIndexOf(identifierSet);
        if (npos==-1) {
            return null;
        }
        if (pos==npos) {
            return null;
        }
        String result = str.substring(pos, npos);
        pos = npos;
        return result;
    }
    
    private final int nextIndexOf(char c) {
        int len = chars.length;
        for (int p=pos;p<len;p++) {
            if (chars[p]==c) {
                return p;
            }
        }
        return -1;
    }
    
    private final int nextIndexOf(int charsetBitfield[]) {
        int len = chars.length;
        for (int p=pos;p<len;p++) {
            if (TamunoUtils.bitfieldGet(charsetBitfield, chars[p])!=0) {
                return p;
            }
        }
        return -1;
    }
    
    private final int endIndexOf(int charsetBitfield[]) {
        int len = chars.length;
        for (int p=pos;p<len;p++) {
            if (TamunoUtils.bitfieldGet(charsetBitfield, chars[p])==0) {
                return p;
            }
        }
        return len;
    }
    
    public static void main(String args[]) {
        try {
            SqlGenScanner scanner = new SqlGenScanner();
            //ArrayList<SQLGenToken> tokens = scanner.scanString("SELECT @a, count(*) as @b:int, @c:Date FROM #table [WHERE { user_id=$user_id:int } [AND age>=$min_age:int]]");
            ArrayList<SQLGenToken> tokens = scanner.scanString("SELECT [] { @user_id:int, [ ?test 'O{K' as test, ] @user_name:String, @birthdate:Date } FROM users [ WHERE [user_name=$user_name] [AND] [active=$active:int] ] LIMIT 1;");
            for (SQLGenToken t : tokens) {
                System.out.println(t.type.toString() + " '" + t.value+"' of type "+t.vartype);
            }
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }
    
    
}
