const {test} = require('node:test');
const assert = require('node:assert/strict');
const search = require('../recipe-ingredient-search.js');
const records = search.prepare([
 {title:'香菇的标题不参与食材检索', ingredients:[{name:'海鲜菇',role:'main',search_terms:['海鲜菇','蘑菇']},{name:'蚝油',role:'optional',search_terms:['蚝油']}]},
 {title:'菜谱二',ingredients:[{name:'西红柿',role:'main',search_terms:['西红柿','番茄']},{name:'鸡蛋',role:'main',search_terms:['鸡蛋']}]}
]);
test('aliases and parent groups match without sibling or title matches',()=>{
 assert.equal(search.matches(records[0],'蘑菇'),true);
 assert.equal(search.matches(records[0],'香菇'),false);
 assert.equal(search.matches(records[1],'番茄 鸡蛋'),true);
 assert.equal(search.matches(records[1],'番茄 排骨'),false);
});
test('optional ingredient exclusion and empty search',()=>{
 assert.equal(search.matches(records[0],'蚝油',true),true);
 assert.equal(search.matches(records[0],'蚝油',false),false);
 assert.equal(search.matches(records[0],''),true);
});
test('old indexes remain usable and matching does not mutate them',()=>{
 const raw=[{title:'标题',ingredients:[{name:'嫩豆腐',role:'main'}]}];
 const prepared=search.prepare(raw);
 assert.equal(search.matches(prepared[0],'豆腐'),true);
 assert.equal('keys' in raw[0].ingredients[0],false);
});
