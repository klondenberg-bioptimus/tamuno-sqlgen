/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 *
 * @author kai
 * @TODO Documentation
 */
public class BaseSQLApi {
    
    protected DBConnectionProvider connectionProvider;
    protected ISQLDialectUtil sqlDialectUtil = GenericSQLDialectUtil.instance;

    public void setConnectionProvider(DBConnectionProvider connectionProvider) {
        this.connectionProvider = connectionProvider;
    }

    public void setSqlDialectUtil(ISQLDialectUtil sqlDialectUtil) {
        this.sqlDialectUtil = sqlDialectUtil;
    }
   

}
