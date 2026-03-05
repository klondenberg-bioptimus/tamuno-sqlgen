/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

/**
 *
 * @author kai
 */
public interface ISQLDialectUtil {
    
    /**
     * Escapes a string value in such a way that it can be safely used within sql strings. That is,
     * ' is replaced by \'
     * @param value String value to be escaped
     * @return escaped String
     */
    public String escapeValue(String value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Integer value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Long value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Short value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Double value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Float value);
    
    /**
     * equivalent to escapeValue(value.toString())
     * @see escapeValue(String)
     */
    public  String escapeValue(Object value);
}
