/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.sqlgen.automate;

import java.util.HashMap;

/**
 * @author kai
 * @TODO Documentation of class AutomaticGenerators
 */
public class AutomaticGenerators {
    
    public static final HashMap<String,ITableCodeGenerator> registry = new HashMap<String,ITableCodeGenerator>();
    
    static {
        registry.put("CRUDS", new CrudsCGen());
        registry.put("Insert Row", new InsertRowCGen());
        registry.put("Update Row", new UpdateRowCGen());
        registry.put("Delete Row", new DeleteRowCGen());
        registry.put("Select Row", new SelectRowCGen());
        registry.put("List Rows", new ListRowsCGen());
        
    }
    
}
