/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

/**
 *
 * @author kai
 */
public class GenericSQLDialectUtil implements ISQLDialectUtil {

    public static final GenericSQLDialectUtil instance = new GenericSQLDialectUtil();
    
    // Singleton which may be helpful for derived classes. Therefore protected constructor.
    protected GenericSQLDialectUtil() {
    }
    
    /**
     * Escapes a string value in such a way that it can be safely used within sql strings. That is,
     * ' is replaced by \'
     * @param value String value to be escaped
     * @return escaped String
     */
    public  String escapeValue(String value) {
        return "'" + value.replace("'", "\\'") + "'";
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Integer value) {
        return value.toString();
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Long value) {
        return value.toString();
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Short value) {
        return value.toString();
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Double value) {
        return value.toString();
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Float value) {
        return value.toString();
    }
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Object value) {
        return escapeValue(value.toString());
    }
}
