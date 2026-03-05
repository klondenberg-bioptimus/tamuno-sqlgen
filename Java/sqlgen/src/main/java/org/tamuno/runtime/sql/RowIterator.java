/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.logging.Level;
import java.util.logging.Logger;

public class RowIterator<T extends TypedRow> implements Iterator<T>, Iterable<T> {
    private ResultSet rs;
    private boolean hasNext;
    T currentRow = null;
    private SQLException sqlException;

    private static void throwAsRuntimeException(Exception ex) {
        RuntimeException rt = new RuntimeException(ex.getClass().getName());
        rt.initCause(ex);
        throw rt;
    }
        
    public RowIterator(ResultSet rs, Class<T> rowClass) throws SQLException {
         this.rs = rs;
         if (rs==null) {
             hasNext = false;
         } else {
             try {
                 currentRow = rowClass.newInstance();
             } catch (InstantiationException ex) {
                throwAsRuntimeException(ex);
            } catch (IllegalAccessException ex) {
                throwAsRuntimeException(ex);
            } 
            hasNext = rs.next();
         }
    }

    public SQLException getSqlException() {
        return sqlException;
    }
    
    public ArrayList<T> getAll() throws SQLException {
        return getAll(Integer.MAX_VALUE);
    }
    
    public ArrayList<T> getAll(int maxCount) throws SQLException {
        ArrayList<T> result = new ArrayList<T>();
        try {
            int i=0;
            for (T e : this) {
                if (i++==maxCount) {
                    break;
                }
                result.add((T) e.clone());
            }
        } finally {
            this.close();
        }
        return result;
    }
    
    public void close() throws SQLException {
        if (rs==null) {
            return;
        }
        rs.close();
        rs = null;
        hasNext = false;
    }
    
    private void iterate() {
        if (hasNext) {
            try {
                currentRow.loadResultSetRow(rs);
                hasNext = rs.next();
                if (!hasNext) {
                    this.close();
                }
            } catch (SQLException ex) {
                this.sqlException = ex;
            }
        } else {
            currentRow = null;
        }
               
    }

    public boolean hasNext() {
        return hasNext;
    }
    
    /*
     * Returns last row returned from next() 
     */
    public T current() {
        return currentRow;
    }
    
    /**
     * Returns next row and closes the connection and result set.
     * 
     * @return a sin
     * @throws java.sql.SQLException
     */
    public T get() throws SQLException {
        iterate();
        close();
        return currentRow;
    }
    
    /*
     * Be careful that the returned object is re-used. To make a copy of it for later use, use the
     * clone() method on the result !
     */
    public T next() {
        iterate();
        return currentRow;
    }

    public void remove() {
        throw new UnsupportedOperationException("Removal not supported");
    }

    public Iterator<T> iterator() {
        return this;
    }
    
    
}
